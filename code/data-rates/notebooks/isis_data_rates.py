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
def _():
    # Streaming
    src_name_bytes, msg_id_bytes, ref_time_bytes, ref_time_index_bytes = 16, 8, 8, 8
    stream_frame_bytes = src_name_bytes + msg_id_bytes + ref_time_bytes + ref_time_index_bytes

    tof_bytes, pixel_id_bytes, diag_bytes = 4, 4, 12
    stream_event_bytes = tof_bytes + pixel_id_bytes + diag_bytes

    # NeXus
    event_index_bytes, event_time_zero_bytes, frame_comp_ratio = 8, 8, 2.5
    nexus_frame_bytes = (event_index_bytes + event_time_zero_bytes) / frame_comp_ratio

    event_id_bytes, event_time_offset_bytes, event_comp_ratio = 4, 4, 1.3
    nexus_event_bytes = (event_id_bytes + event_time_offset_bytes) / event_comp_ratio
    return (
        nexus_event_bytes,
        nexus_frame_bytes,
        stream_event_bytes,
        stream_frame_bytes,
    )


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

        CREATE OR REPLACE TABLE data_sizes AS (
          SELECT * FROM (
            VALUES
              ('ev44_src_name_bytes', 16),
              ('ev44_msg_id_bytes', 8),
              ('ev44_ref_time_bytes', 8),
              ('ev44_ref_time_index_bytes', 8),
              ('ev44_tof_bytes', 4),
              ('ev44_pixel_id_bytes', 4),
              ('event_diag', 12),
              ('nxs_event_index', 8),
              ('nxs_event_time_zero', 8),
              ('nxs_frame_comp_ratio', 2.5),
              ('nxs_event_id', 4),
              ('nxs_event_time_offset', 4),
              ('nxs_event_comp_ratio', 1.3),
          ) AS t (fieldname, num_bytes)
        );

        """
    )
    return


@app.cell
def _(RUN_SUMMARY_DIR, mo):
    _df = mo.sql(
        f"""
        -- Run data tables
        -- Exclude runs where the total number of events recorded by the DAE counter is less
        -- than recorded in the files.
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
                -- AND journal_total_mevents >= (nxs_detector_mcounts + nxs_monitor_mcounts)
        );
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- debugging cell
        -- SELECT
        --   beamline,
        --   journal_total_mevents,
        --   nxs_detector_mcounts + nxs_monitor_mcounts
        -- FROM
        --   run_summary
        -- WHERE beamline = 'LARMOR'

        -- SELECT
        --     beamline,
        --     cycle_name,
        --     (SUM(duration) / 3600 / 24) AS total_duration_days
        -- FROM run_summary
        -- GROUP BY beamline, cycle_name
        -- ORDER BY beamline, cycle_name
        """
    )
    return


@app.cell
def _(beamline, mo, run_summary):
    run_summaries_df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE run_stats AS (
          SELECT
                rs.beamline,
                CONCAT('TS', b.target_station) as target_station,
                ROUND(QUANTILE(duration, 0.50)) as p50_duration,
                ROUND(QUANTILE(duration, 0.99)) as p99_duration,
            	ROUND(QUANTILE(good_frames, 0.99), 1) as p99_good_frames,
            	ROUND(QUANTILE(framerate_hz, 0.99), 1) as p99_framerate_hz,
                ROUND(QUANTILE(detector_mevents_per_frame, 0.99), 4) as p99_det_mevents_frame,
                ROUND(QUANTILE(monitor_mevents_per_frame, 0.99), 4) as p99_mon_mevents_frame,
                MAX(number_of_time_channels) as max_number_time_channels,
                MEDIAN(number_periods) as med_number_periods,
                MAX(number_monitors) as max_number_monitors
            FROM
                run_summary rs
            JOIN beamline b ON rs.beamline = b.beamline
            GROUP BY
                rs.beamline, b.target_station
        	ORDER BY rs.beamline
        );
        select * from run_stats;
        """
    )
    return


@app.cell
def _(
    mo,
    nexus_event_bytes,
    nexus_frame_bytes,
    run_stats,
    stream_event_bytes,
    stream_frame_bytes,
):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE FUNCTION to_mbps(framerate, mevents_per_frame) AS (
          ROUND(framerate * ({stream_frame_bytes} + mevents_per_frame * 1e6 * {stream_event_bytes}) * 8 / 1e6, 4)
        );

        CREATE OR REPLACE FUNCTION to_nxs_gbhr(framerate, mevents_per_frame) AS (
          ROUND((3600 * framerate) * ({nexus_frame_bytes} + mevents_per_frame * 1e6 * {nexus_event_bytes})/1e9, 4)
        );

        CREATE OR REPLACE TABLE current_rates AS (
            SELECT
              beamline,
              target_station,
              TO_MBPS(p99_framerate_hz, p99_det_mevents_frame) AS "P99 Detector rate (Mbps)",
              TO_MBPS(p99_framerate_hz, p99_mon_mevents_frame) AS "P99 Monitor rate (Mbps)",
              TO_NXS_GBHR(p99_framerate_hz, p99_det_mevents_frame) AS "P99 NeXus det rate (GB/hr)",
              TO_NXS_GBHR(p99_framerate_hz, p99_mon_mevents_frame) AS "P99 NeXus mon rate (GB/hr)"
            FROM run_stats
        );
        select * from current_rates;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE rollout_info AS (
            SELECT * FROM (
                VALUES
                    ('HRPD-X',     'HRPD',    DOUBLE '5.25', DOUBLE '1', DATE '2027-11-01'),
                    ('SuperMUSR',  'MUSR',    DOUBLE '12.5', DOUBLE '0', DATE '2028-04-01'),
                    ('SANDALS-II', 'SANDALS', DOUBLE '10',   DOUBLE '2.5', DATE '2028-10-01'),
                    ('WISH-II',    'WISH',    DOUBLE '4',    DOUBLE '1', DATE '2030-10-01'),
                    ('MUSHROOM',   'LET',     DOUBLE '50',   DOUBLE '1', DATE '2030-10-01'),
                    ('TOSCA+',     'TOSCA',   DOUBLE '50',   DOUBLE '1', DATE '2031-10-01'),  -- WHERE DID I GET THIS FROM?
                    ('OSIRIS+',    'OSIRIS',  DOUBLE '50',   DOUBLE '1', DATE '2031-10-01')   -- WHERE DID I GET THIS FROM?
            ) AS t (beamline, baseline, det_sf, mon_sf, date_online)
        );
        select * from rollout_info order by date_online asc;
        """
    )
    return


@app.cell
def _(current_rates, mo, rollout_info):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE streaming_rollout AS (
            WITH tmp AS (
                SELECT
                  e.beamline,
                  e.date_online,
                  ROUND(cr."P99 Detector rate (Mbps)" * det_sf, 4) AS "P99 Detector rate (Mbps)",
                  ROUND(cr."P99 Monitor rate (Mbps)" * mon_sf, 4) AS "P99 Monitor rate (Mbps)",
                  ROUND(cr."P99 Detector rate (Mbps)" * det_sf + cr."P99 Monitor rate (Mbps)" * mon_sf, 4) AS "Total rate (Mbps)",
                FROM
                  rollout_info e
                LEFT JOIN current_rates cr ON e.baseline = cr.beamline  
            )
            SELECT
              beamline as Beamline,
        	  date_online AS "Date Online",
              "P99 Detector rate (Mbps)",
              "P99 Monitor rate (Mbps)",
              "Total rate (Mbps)",
              ROUND(SUM("Total rate (Mbps)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative rate (Mbps)",
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
                  ROUND(cr."P99 NeXus det rate (GB/hr)" * det_sf, 4) AS "P99 NeXus det rate (GB/hr)",
                  ROUND(cr."P99 NeXus mon rate (GB/hr)" * mon_sf, 4) AS "P99 NeXus mon rate (GB/hr)",
                FROM
                  rollout_info e
                LEFT JOIN current_rates cr ON e.baseline = cr.beamline  
            )
            SELECT
              beamline as Beamline,
        	  date_online AS "Date Online",
              "P99 NeXus det rate (GB/hr)",
              "P99 NeXus mon rate (GB/hr)",
              ROUND(tmp."P99 NeXus det rate (GB/hr)" + tmp."P99 NeXus mon rate (GB/hr)", 4) AS "NeXus total rate (GB/hr)",
              ROUND(SUM("P99 NeXus det rate (GB/hr)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative Nexus det (GB/hr)",
              ROUND(SUM("P99 NeXus mon rate (GB/hr)") OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative Nexus mon (GB/hr)"
            FROM tmp
            ORDER BY date_online ASC
        );
        select * from nexus_rollout;
        """
    )
    return


@app.cell
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
