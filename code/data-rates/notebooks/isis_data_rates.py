import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import dotenv
    import marimo as mo
    import os

    dotenv.load_dotenv()

    RUN_SUMMARY_JSON_DIR = os.environ["RUN_SUMMARY_JSON_DIR"]
    print(f"Loading run summaries from '{RUN_SUMMARY_JSON_DIR}'")
    return RUN_SUMMARY_JSON_DIR, mo


@app.cell
def _(RUN_SUMMARY_JSON_DIR, mo):
    _df = mo.sql(
        f"""
        create or replace table run_summary AS (
            SELECT
                *
            FROM
                read_json('{RUN_SUMMARY_JSON_DIR}/HRPD*.json')
            WHERE
                duration > 0.0
                AND good_frames > 0
                AND icp_error_count = 0
                AND total_mevents >= (total_detector_mevents + total_monitor_mevents)
        );
        -- select * from run_summary;
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
        with
            beamline_target_mapping as (
                select
                    *
                from
                    read_csv('./beamline_target_mapping.csv')
            ),
            target_station as (
                select
                    *
                from
                    read_csv('./target_station.csv')
            ),
            events_per_frame_stats as (
                select
                    beamline,
                    max(total_detector_mevents / good_frames) as max_det_mevents_per_frame,
                    quantile(total_detector_mevents / good_frames, 0.99) as p99_det_mevents_per_frame,
                    quantile(total_detector_mevents / good_frames, 0.999) as p999_det_mevents_per_frame,
                    max(total_monitor_mevents / good_frames) as max_mon_mevents_per_frame
                from
                    run_summary
                group by
                    beamline
            )
        select
            e.beamline,
            bt.target_station,
            tgt.mode_label,
            tgt.framerate_hz,
            framerate_hz * (
                ({ev44_header_bits} / 1_000_000) + max_det_mevents_per_frame * {ev44_per_event_bits}
            ) as max_det_mbits_sec,
            framerate_hz * (
                ({ev44_header_bits} / 1_000_000) + p99_det_mevents_per_frame * {ev44_per_event_bits}
            ) as p99_det_mbits_sec,
            framerate_hz * (
                ({ev44_header_bits} / 1_000_000) + p999_det_mevents_per_frame * {ev44_per_event_bits}
            ) as p999_det_mbits_sec
        from
            events_per_frame_stats e
            join beamline_target_mapping bt on e.beamline = bt.beamline
            join target_station tgt on bt.target_station = tgt.number;
        """
    )
    return


@app.cell(hide_code=True)
def _():
    return


if __name__ == "__main__":
    app.run()
