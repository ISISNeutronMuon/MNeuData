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

    # Data
    FRAME_DATA_EXCEL = Path() / "isis_frame_data.xlsx"
    REPO_DATA_DIR = Path() / "data"
    RUN_SUMMARY_DIR = Path(os.environ["RUN_SUMMARY_DIR"])


    print(f"Loading run summaries from '{RUN_SUMMARY_DIR}'")
    return REPO_DATA_DIR, RUN_SUMMARY_DIR, mo


@app.cell
def _(REPO_DATA_DIR, mo):
    _df = mo.sql(
        f"""
        -- Repo, static data
        CREATE OR REPLACE TABLE beamline AS (
            SELECT
                beamline,
                target_station
            FROM
                read_json('{REPO_DATA_DIR}/beamline.json')
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
                AND journal_total_mevents >= (nxs_detector_mcounts + nxs_monitor_mcounts)
        );
        """
    )
    return


@app.cell
def _(beamline, mo, run_summary):
    run_summaries_df = mo.sql(
        f"""
        -- Max rates
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
        -- SELECT
        --     rs.beamline,
        --     CONCAT('TS', b.target_station) as target_station,
        --     p50_duration,
        --     p99_duration,
        --     p99_good_frames,
        --     p99_framerate_hz,
        --     p99_det_mevents_frame,
        --     p99_mon_mevents_frame,
        --     max_number_time_channels,
        --     med_number_periods,
        --     max_number_monitors
        -- FROM
        --     run_stats rs
        -- JOIN beamline b ON rs.beamline = b.beamline
        -- ORDER BY rs.beamline;
        """
    )
    return


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
              TO_MBPS(p99_framerate_hz, p99_det_mevents_frame) AS "Detector rate (Mbps)",
              TO_MBPS(p99_framerate_hz, p99_mon_mevents_frame) AS "Monitor rate (Mbps)",
              TO_NXS_GBHR(p99_framerate_hz, p99_det_mevents_frame) AS "NeXus det rate (GB/hr)",
              TO_NXS_GBHR(p99_framerate_hz, p99_mon_mevents_frame) AS "NeXus mon rate (GB/hr)"
            FROM run_stats
        );
        select * from current_rates
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE endeavour_info AS (
            SELECT * FROM (
                VALUES
                    ('HRPD-X',     'HRPD',    DOUBLE '5.25', DOUBLE '1', DATE '2027-11-01'),
                    ('SuperMUSR',  'MUSR',    DOUBLE '12.5', DOUBLE '0', DATE '2028-04-01'),
                    ('SANDALS-II', 'SANDALS', DOUBLE '10',   DOUBLE '2.5', DATE '2028-10-01'),
                    ('WISH-II',    'WISH',    DOUBLE '4',    DOUBLE '1', DATE '2030-10-01'),
                    ('MUSHROOM',   'LET',     DOUBLE '50',   DOUBLE '1', DATE '2030-10-01'),
                    ('TOSCA+',     'TOSCA',   DOUBLE '50',   DOUBLE '1', DATE '2031-10-01'),
                    ('OSIRIS+',    'OSIRIS',  DOUBLE '50',   DOUBLE '1', DATE '2031-10-01')
            ) AS t (beamline, baseline, det_sf, mon_sf, date_online)
        );
        select * from endeavour_info order by date_online asc;
        """
    )
    return


@app.cell
def _(current_rates, endeavour_info, mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE projections AS (
            SELECT
              e.beamline,
              ROUND("Detector rate (Mbps)" * det_sf, 4) AS "Detector rate (Mbps)",
              ROUND("Monitor rate (Mbps)" * mon_sf, 4) AS "Monitor rate (Mbps)",
              ROUND("NeXus det rate (GB/hr)" * det_sf, 4) AS "NeXus det rate (GB/hr)",
              ROUND("NeXus mon rate (GB/hr)" * mon_sf, 4) AS "NeXus mon rate (GB/hr)",
            e.date_online,
            FROM endeavour_info e
            LEFT JOIN current_rates cr ON e.baseline = cr.beamline
            ORDER BY beamline
        );
        """
    )
    return


@app.cell(hide_code=True)
def _(mo, projections):
    _df = mo.sql(
        f"""
        SELECT
          date_online,
          beamline,
          ROUND("Detector rate (Mbps)" + "Monitor rate (Mbps)", 4) AS "Total rate (Mbps)",
          ROUND(SUM("Detector rate (Mbps)" + "Monitor rate (Mbps)")  OVER (ORDER BY date_online ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 4) AS "Cumulative rate (Mbps)"
        FROM projections
        ORDER BY date_online;
        """
    )
    return


@app.cell
def _():
    #frame_data_df.write_excel(FRAME_DATA_EXCEL, worksheet="Sheet1", table_name="data")
    return


if __name__ == "__main__":
    app.run()
