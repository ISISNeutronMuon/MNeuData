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
    RUN_SUMMARY_JSON_DIR = Path(os.environ["RUN_SUMMARY_JSON_DIR"])

    print(f"Loading run summaries from '{RUN_SUMMARY_JSON_DIR}'")
    return REPO_DATA_DIR, RUN_SUMMARY_JSON_DIR, mo


@app.cell
def _(REPO_DATA_DIR, RUN_SUMMARY_JSON_DIR, mo):
    _df = mo.sql(
        f"""
        -- CORE tables
        CREATE OR REPLACE TABLE beamline AS (
            SELECT
                *
            FROM
                read_json('{REPO_DATA_DIR}/beamline.json')
        );

        CREATE OR REPLACE TABLE target_station AS (
            SELECT
                *
            FROM
                read_json('{REPO_DATA_DIR}/target_station.json')
        );

        -- Exclude runs where ICP recorded errors such as reading invalid memory
        -- or where the total number of events recorded by the DAE counter is less
        -- than recorded in the files.
        CREATE OR REPLACE TABLE run_summary AS (
            SELECT
                *
            FROM
                read_json('{RUN_SUMMARY_JSON_DIR}/*.json')
            WHERE
                duration > 0.0
                AND good_frames > 0
                AND total_mevents >= (total_detector_mevents + total_monitor_mevents)
        );

        -- DEBUGGING
        select * from run_summary;
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
def _(mo, run_summary):
    _df = mo.sql(
        f"""
        -- Raw events per frame
        CREATE OR REPLACE TABLE events_per_frame AS (
            SELECT
                beamline,
                run_number,
                (total_detector_mevents / good_frames) AS det_mevents_per_frame,
                (total_monitor_mevents / good_frames) AS mon_mevents_per_frame
            FROM
                run_summary
        );

        CREATE OR REPLACE TABLE events_per_frame_stats AS (
            SELECT
                beamline,
                max(det_mevents_per_frame) AS max_det_mevents_per_frame,
                quantile(det_mevents_per_frame, 0.999) AS p999_det_mevents_per_frame,
                max(mon_mevents_per_frame) AS max_mon_mevents_per_frame,
                quantile(mon_mevents_per_frame, 0.999) AS p999_mon_mevents_per_frame,
            FROM
                events_per_frame
            GROUP BY
                beamline
        );
        """
    )
    return


@app.cell
def _(
    beamline,
    ev44_header_bits,
    ev44_per_event_bits,
    events_per_frame_stats,
    mo,
    target_station,
):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO to_mbits_sec (framerate_hz, evts_per_frame) AS framerate_hz * (
            ({ev44_header_bits} / 1_000_000) + evts_per_frame * {ev44_per_event_bits}
        );

        SELECT
            e.beamline,
            bt.target_station,
            tgt.mode_label,
            tgt.framerate_hz,
            to_mbits_sec (tgt.framerate_hz, max_det_mevents_per_frame) AS max_det_mbits_sec,
            to_mbits_sec (tgt.framerate_hz, p999_det_mevents_per_frame) AS p999_det_mbits_sec,
            to_mbits_sec (tgt.framerate_hz, max_mon_mevents_per_frame) AS max_mon_mbits_sec,
            to_mbits_sec (tgt.framerate_hz, p999_mon_mevents_per_frame) AS p999_mon_mbits_sec,
        FROM
            events_per_frame_stats e
            JOIN beamline bt ON e.beamline = bt.beamline
            JOIN target_station tgt ON bt.target_station = tgt.number
        """
    )
    return


if __name__ == "__main__":
    app.run()
