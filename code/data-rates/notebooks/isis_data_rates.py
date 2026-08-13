import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import os
    from pathlib import Path
    import dotenv
    import marimo as mo

    dotenv.load_dotenv()

    REPO_DATA_DIR = Path() / "data"
    RUN_SUMMARY_DIR = Path(os.environ["RUN_SUMMARY_DIR"])

    print(f"Loading run summaries from '{RUN_SUMMARY_DIR}'")
    return REPO_DATA_DIR, RUN_SUMMARY_DIR, mo


@app.cell(hide_code=True)
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
                beamline,
                run_number,
                cycle,
            	title,
                frame_sync,
                raw_frames,
                good_frames,
                duration,
                total_mevents as journal_total_mevents,
                total_detector_mevents,
                total_monitor_mevents,
                round(raw_frames/duration, 1) as framerate_hz
            FROM
                read_parquet('{RUN_SUMMARY_DIR}/*.parquet')
            WHERE
                frame_sync NOT ILIKE '%internal%'
                AND duration > 0.0
                AND raw_frames > 1
                AND good_frames > 1
                AND journal_total_mevents > 0
                AND journal_total_mevents >= (total_detector_mevents + total_monitor_mevents)
        );

        -- select * from run_summary where beamline = 'HRPD' order by framerate_hz asc;
        """
    )
    return


@app.cell
def _():
    # ---------------------
    # Event type information
    # Matches ESS ev44 schema:
    # https://github.com/ess-dmsc/streaming-data-types/blob/5fde74d8eb69658073735984acc9465ed10870b1/schemas/ev44_events.fbs
    #
    # Assumptions:
    #   - a single Event44Message per ISIS frame
    #   - source_name assumes a maximum char length=16
    # ---------------------
    source_name_bits = 16 * 8
    message_id_bits = 64
    reference_time_bits = 64  # single frame
    ev44_header_bits = source_name_bits + message_id_bits + reference_time_bits

    reference_time_index = 32
    time_of_flight = 32
    pixel_id = 32
    ev44_per_event_bits = reference_time_index + time_of_flight + pixel_id

    print("---- Data sizes ----")
    print(f"ev44_header_bits = {ev44_header_bits} bit")
    print(f"ev44_per_event_bits = {ev44_per_event_bits} bit")
    return ev44_header_bits, ev44_per_event_bits


@app.cell
def _(ev44_header_bits, ev44_per_event_bits, mo, run_summary):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO to_mbits_sec (framerate_hz, mevts_per_frame) AS framerate_hz * (
            ({ev44_header_bits} / 1_000_000) + mevts_per_frame * {ev44_per_event_bits}
        );

        CREATE OR REPLACE TABLE data_rates AS (
            SELECT
                beamline,
                run_number,
                framerate_hz,
                TO_MBITS_SEC(framerate_hz, total_detector_mevents / good_frames) AS det_mbits_sec,
                TO_MBITS_SEC(framerate_hz, total_monitor_mevents / good_frames) AS mon_mbits_sec,
            FROM
                run_summary
        );
        """
    )
    return


@app.cell
def _(beamline, data_rates, mo):
    _df = mo.sql(
        f"""
        SELECT
            d.beamline,
            MIN(d.framerate_hz) AS min_framerate_hz,
            MAX(d.framerate_hz) AS max_framerate_hz,
            MAX(det_mbits_sec) AS max_det_mbits_sec,
            QUANTILE(det_mbits_sec, 0.999) AS p999_det_mbits_sec,
            MAX(mon_mbits_sec) AS max_mon_mbits_sec,
            QUANTILE(mon_mbits_sec, 0.999) AS p999_mon_mbits_sec
        FROM
            data_rates d
        JOIN beamline b ON d.beamline = b.beamline
        GROUP BY
            d.beamline
        """
    )
    return


if __name__ == "__main__":
    app.run()
