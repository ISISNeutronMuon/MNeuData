import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import dotenv
    import marimo as mo

    dotenv.load_dotenv()

    FILENAME_XLSX = Path() / "isis_data_rates.xlsx"
    REPO_DATA_DIR = Path() / "data"
    RUN_SUMMARY_DIR = Path(os.environ["RUN_SUMMARY_DIR"])
    XLSX_TABLE_STYLE = "Table Style Medium 2"

    print(f"Loading run summaries from '{RUN_SUMMARY_DIR}'")
    return FILENAME_XLSX, REPO_DATA_DIR, RUN_SUMMARY_DIR, XLSX_TABLE_STYLE, mo


@app.cell
def _(REPO_DATA_DIR, mo):
    _df = mo.sql(
        f"""
        -- Static data
        CREATE OR REPLACE TABLE beamline AS (
            SELECT
                beamline,
                target_station
            FROM
                read_json('{REPO_DATA_DIR}/beamline.json')
        );

        CREATE OR REPLACE TABLE mneudata_rollout_info AS (
            SELECT * FROM (
                VALUES
                    ('HRPD-X',     'HRPD',    DOUBLE '5.25', DOUBLE '1', DATE '2027-11-01'),
                    ('SuperMUSR',  'MUSR',    DOUBLE '4', DOUBLE '0', DATE '2028-04-01'),
                    ('SANDALS-II', 'SANDALS', DOUBLE '10',   DOUBLE '2.5', DATE '2028-10-01'),
                    ('WISH-II',    'WISH',    DOUBLE '4',    DOUBLE '1', DATE '2030-10-01'),
                    ('MUSHROOM',   'LET',     DOUBLE '50',   DOUBLE '1', DATE '2030-10-01'),
                    ('TOSCA+',     'TOSCA',   DOUBLE '10',   DOUBLE '1', DATE '2031-10-01'), 
                    ('OSIRIS+',    'OSIRIS',  DOUBLE '10',   DOUBLE '1', DATE '2031-10-01')
            ) AS t (beamline, baseline, det_sf, mon_sf, date_online)
        );
        """
    )
    return


@app.cell
def _():
    # Data sizes
    # See https://github.com/ISISComputingGroup/streaming-data-types/tree/main/schemas

    src_name_bytes, msg_id_bytes, ref_time_bytes, ref_time_index_bytes, tof_bytes, pixel_id_bytes = 16, 8, 8, 4, 4, 4 
    ev44_bytes = (src_name_bytes + msg_id_bytes + ref_time_bytes + ref_time_index_bytes + tof_bytes + pixel_id_bytes)
    return (ev44_bytes,)


@app.cell
def _(ev44_bytes, mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE FUNCTION to_mbps_ev44(framerate, mevents_per_frame) AS (
          ROUND(framerate * mevents_per_frame * {ev44_bytes} * 8, 4)
        );

        CREATE OR REPLACE FUNCTION to_msg_kbytes_ev44(mevents_per_frame) AS (
          ROUND(1e3 * mevents_per_frame * {ev44_bytes}, 4)
        );
        """
    )
    return


@app.cell
def _(RUN_SUMMARY_DIR, mo):
    _df = mo.sql(
        f"""
        -- Raw run data tables
        -- Exclude runs where they are "obviously" bad
        CREATE OR REPLACE TABLE run_summary AS (
            SELECT
                j.beamline,
                j."cycle" AS cycle_name,
                j.run_number,
                j.event_mode,
                j.frame_sync,
                j.raw_frames,
                j.good_frames,
                j.duration,
                j.total_mevents as journal_total_mevents,
                j.number_periods,
                j.number_spectra,
                j.number_time_channels[1] AS number_of_time_channels,
                n.number_monitors,
                n.total_detector_mcounts AS nxs_detector_mcounts,
                n.total_monitor_mcounts AS nxs_monitor_mcounts,
                ROUND(n.file_size_bytes / 1000**2, 4) AS nxs_file_size_mbytes,
                ROUND(j.good_frames/j.duration, 1) as framerate_hz,
                (nxs_detector_mcounts / good_frames) AS detector_mevents_per_frame,
                (nxs_monitor_mcounts / good_frames) AS monitor_mevents_per_frame,
            FROM
                read_parquet('{RUN_SUMMARY_DIR}/*_journal.parquet') j
            JOIN
                (SELECT * FROM read_parquet('{RUN_SUMMARY_DIR}/*_nexus.parquet')) n ON
                    j.beamline = n.beamline AND j."cycle" = n."cycle" AND j.run_number = n.run_number
            WHERE
                frame_sync NOT ILIKE '%internal%'
                AND duration > 0.0
                AND raw_frames > 1
                AND good_frames > 1
                AND framerate_hz < 55
                AND journal_total_mevents > 0
                AND nxs_detector_mcounts > 0
                AND nxs_monitor_mcounts >= 0
        );
        """
    )
    return


@app.cell
def _(ev44_bytes, mo):
    _df = mo.sql(
        f"""
        -- debugging cell
        -- select

        --     (2e9/3600),
        --     beamline,
        --     run_number,
        --     detector_mevents_per_frame*1e6*framerate_hz as det_events_sec
        --     -- det_events_sec * {ev44_bytes} * 8 / 1e6
        --     --monitor_mevents_per_frame*1e6*framerate_hz*3600*4 as mon_events_hr,

        -- from run_summary where beamline='MUSR'
        """
    )
    return


@app.cell
def _(beamline, mneudata_rollout_info, mo, run_summary):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE data_rates_per_run AS (
          WITH current_suite AS (
            SELECT
              rs.beamline,
              CONCAT('TS', b.target_station) AS target_station,
              run_number,
              false AS endeavour,
              to_mbps_ev44(rs.framerate_hz, rs.detector_mevents_per_frame) AS det_events_mbps,
              to_mbps_ev44(rs.framerate_hz, rs.monitor_mevents_per_frame) AS mon_events_mbps,
              to_msg_kbytes_ev44(rs.detector_mevents_per_frame) AS det_msg_size_kbytes,
              to_msg_kbytes_ev44(rs.monitor_mevents_per_frame) AS mon_msg_size_kbytes
            FROM
              run_summary rs
            JOIN beamline b ON rs.beamline = b.beamline
          ),
          endeavour AS (
        	SELECT
              m.beamline,
              c.target_station,
              c.run_number,
              true AS endeavour,
              ROUND(det_events_mbps * m.det_sf, 4) AS det_events_mbps,
              ROUND(mon_events_mbps * m.mon_sf, 4) AS mon_events_mbps,
              ROUND(det_msg_size_kbytes * m.det_sf, 4) AS det_msg_size_kbytes,
              ROUND(mon_msg_size_kbytes * m.mon_sf, 4) AS mon_msg_size_kbytes
            FROM
              mneudata_rollout_info m
            LEFT JOIN current_suite c ON c.beamline = m.baseline
          )

          select * from current_suite
          UNION
          select * from endeavour
        );
        select * from data_rates_per_run where beamline = 'SuperMUSR';
        """
    )
    return


@app.cell
def _(data_rates_per_run, mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE data_rates_stats AS (
          SELECT
            beamline,
            ROUND(QUANTILE(det_events_mbps, 0.5), 4) AS p50_det_events_mbps, 
            ROUND(QUANTILE(mon_events_mbps, 0.5), 4) AS p50_mon_events_mbps, 
            ROUND(QUANTILE(det_events_mbps, 0.99), 4) AS p99_det_events_mbps, 
            ROUND(QUANTILE(mon_events_mbps, 0.99), 4) AS p99_mon_events_mbps, 
            ROUND(QUANTILE(det_events_mbps + mon_events_mbps, 0.5), 4) AS p50_tot_events_mbps, 
            ROUND(QUANTILE(det_events_mbps + mon_events_mbps, 0.99), 4) AS p99_tot_events_mbps,
            target_station,
            endeavour,
          FROM data_rates_per_run
          GROUP BY
            beamline, target_station, endeavour
        );
        select * from data_rates_stats order by beamline ASC;
        """
    )
    return


@app.cell(disabled=True)
def _(current_rates, mo, rollout_info):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE streaming_rollout AS (
            WITH tmp AS (
                SELECT
                  e.beamline,
                  e.date_online,
                  ROUND(cr."P50 Detector count rate (M/s)" * det_sf, 4) AS "P50 Detector count rate (M/s)",
                  ROUND(cr."P50 Detector rate (Mbps)" * det_sf, 4) AS "P50 Detector rate (Mbps)",
        		  ROUND(cr."P50 Message size (MB)" * det_sf, 4) AS "P50 Message size (MB)",
                  ROUND(cr."P50 Monitor rate (Mbps)" * mon_sf, 4) AS "P50 Monitor rate (Mbps)",
                  ROUND(cr."P50 Detector rate (Mbps)" * det_sf + cr."P50 Monitor rate (Mbps)" * mon_sf, 4) AS "Total P50 rate (Mbps)",
                  ROUND(cr."P75 Detector rate (Mbps)" * det_sf, 4) AS "P75 Detector rate (Mbps)",
        		  ROUND(cr."P75 Message size (MB)" * det_sf, 4) AS "P75 Message size (MB)",
                  ROUND(cr."P75 Monitor rate (Mbps)" * mon_sf, 4) AS "P75 Monitor rate (Mbps)",
                  ROUND(cr."P75 Detector rate (Mbps)" * det_sf + cr."P75 Monitor rate (Mbps)" * mon_sf, 4) AS "Total P75 rate (Mbps)",
                  ROUND(cr."P99 Detector rate (Mbps)" * det_sf, 4) AS "P99 Detector rate (Mbps)",
        		  ROUND(cr."P99 Message size (MB)" * det_sf, 4) AS "P99 Message size (MB)",
                  ROUND(cr."P99 Monitor rate (Mbps)" * mon_sf, 4) AS "P99 Monitor rate (Mbps)",
                  ROUND(cr."P99 Detector rate (Mbps)" * det_sf + cr."P99 Monitor rate (Mbps)" * mon_sf, 4) AS "Total P99 rate (Mbps)",
                FROM
                  rollout_info e
                LEFT JOIN current_rates cr ON e.baseline = cr.beamline  
            )
            SELECT
              beamline as Beamline,
        	  date_online AS "Date Online",
              -- "P50 Detector count rate (M/s)",
              "P50 Detector rate (Mbps)",
              "P50 Message size (MB)",
              "P50 Monitor rate (Mbps)",
              "Total P50 rate (Mbps)",
              "P75 Detector rate (Mbps)",
              "P75 Message size (MB)",
              -- "P75 Monitor rate (Mbps)",
              -- "Total P75 rate (Mbps)",
              "P99 Detector rate (Mbps)",
              "P99 Message size (MB)",
              "P99 Monitor rate (Mbps)",
              "Total P99 rate (Mbps)",
              ROUND(SUM("Total P50 rate (Mbps)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative rate P50 (Mbps)",
              -- ROUND(SUM("Total P75 rate (Mbps)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative rate P75 (Mbps)",
              ROUND(SUM("Total P99 rate (Mbps)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative rate P99 (Mbps)",
            FROM tmp
            ORDER BY date_online ASC
        );
        select * from streaming_rollout;
        """
    )
    return


@app.cell
def _(current_rates, mo, rollout_info):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE nexus_rollout AS (
            WITH tmp AS (
                SELECT
                  e.beamline,
                  e.date_online,
                  ROUND(cr."P50 NeXus det rate (GB/hr)" * det_sf, 4) AS "P50 NeXus det rate (GB/hr)",
                  ROUND(cr."P50 NeXus mon rate (GB/hr)" * mon_sf, 4) AS "P50 NeXus mon rate (GB/hr)",
                  ROUND(cr."P75 NeXus det rate (GB/hr)" * det_sf, 4) AS "P75 NeXus det rate (GB/hr)",
                  ROUND(cr."P75 NeXus mon rate (GB/hr)" * mon_sf, 4) AS "P75 NeXus mon rate (GB/hr)",
                  ROUND(cr."P99 NeXus det rate (GB/hr)" * det_sf, 4) AS "P99 NeXus det rate (GB/hr)",
                  ROUND(cr."P99 NeXus mon rate (GB/hr)" * mon_sf, 4) AS "P99 NeXus mon rate (GB/hr)",
                FROM
                  rollout_info e
                LEFT JOIN current_rates cr ON e.baseline = cr.beamline  
            )
            SELECT
              beamline as Beamline,
        	  date_online AS "Date Online",
              "P50 NeXus det rate (GB/hr)",
              "P50 NeXus mon rate (GB/hr)",
              ROUND(tmp."P50 NeXus det rate (GB/hr)" + tmp."P50 NeXus mon rate (GB/hr)", 4) AS "NeXus total P50 (GB/hr)",
              "P75 NeXus det rate (GB/hr)",
              "P75 NeXus mon rate (GB/hr)",
              ROUND(tmp."P75 NeXus det rate (GB/hr)" + tmp."P75 NeXus mon rate (GB/hr)", 4) AS "NeXus total P75 (GB/hr)",
              "P99 NeXus det rate (GB/hr)",
              "P99 NeXus mon rate (GB/hr)",
              ROUND(tmp."P99 NeXus det rate (GB/hr)" + tmp."P99 NeXus mon rate (GB/hr)", 4) AS "NeXus total P99 (GB/hr)",
            FROM tmp
            ORDER BY date_online ASC
        );
        select * from nexus_rollout;
        """
    )
    return


@app.cell(disabled=True)
def _(FILENAME_XLSX, XLSX_TABLE_STYLE):
    import duckdb
    import xlsxwriter

    if FILENAME_XLSX.exists():
        FILENAME_XLSX.unlink()

    gap = 5
    common_args = dict(table_style=XLSX_TABLE_STYLE)
    with xlsxwriter.Workbook(FILENAME_XLSX) as workbook:
        streaming_rollout_df = duckdb.table("streaming_rollout").pl()
        streaming_rollout_df.write_excel(
            workbook,
            worksheet="Rollout",
            table_name="streaming_rollout",
            **common_args,
        )
        duckdb.table("nexus_rollout").pl().write_excel(
            workbook,
            worksheet="Rollout",
            table_name="nexus_rollout",
            position=(streaming_rollout_df.height + gap, 0),
            **common_args,
        )
        duckdb.table("current_rates").pl().write_excel(
            workbook,
            worksheet="Current rates",
            table_name="current_rates",
            **common_args,
        )
        duckdb.table("rollout_info").pl().write_excel(
            workbook,
            worksheet="Rollout Info",
            table_name="rollout_info",
            **common_args,
        )
        duckdb.table("data_sizes").pl().write_excel(
            workbook,
            worksheet="Data sizes",
            table_name="data_sizes",
            **common_args,
        )
        for ws in workbook.worksheets():
            ws.autofit()
    return


if __name__ == "__main__":
    app.run()
