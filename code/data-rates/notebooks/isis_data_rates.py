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
    return RUN_SUMMARY_JSON_DIR, mo


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


@app.cell(hide_code=True)
def _(RUN_SUMMARY_JSON_DIR, mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE run_summary AS (
            SELECT
                *
            FROM
                read_json('{RUN_SUMMARY_JSON_DIR}')
        );
        select * from run_summary;
        """
    )
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE nexus_summary AS (
            SELECT
                beamline,
                run_number,
                total_detector_mevents,
                total_monitor_mevents
            FROM
                read_csv('./run_summaries/*_nexus.csv')
        );
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE journal_summary AS (
            SELECT
                beamline,
                run_number,
                total_mevents,
                duration,
                good_frames,
                event_mode
            FROM
                read_csv('./run_summaries/*_journal.csv')
        );
        select * from journal_summary where event_mode > 0.
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE icp_debug AS (
            SELECT
                *
            FROM
                read_csv('./run_summaries/*_icp_debug.csv')
        );
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE beamline_target_mapping as (
            SELECT
                *
            FROM
                read_csv('./beamline_target_mapping.csv')
        );
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE target_station as (
            SELECT
              *
            FROM
              read_csv('./target_station.csv')

        );
        """
    )
    return


@app.cell
def _(beamline_target_mapping, icp_debug, journal_summary, mo, nexus_summary):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE event_counts as (
            SELECT
                n.beamline,
                b.target_station,
                n.run_number,
                i.icp_error_count,
                good_frames,
                total_mevents,
                total_detector_mevents as nexus_det_mevents,
                total_monitor_mevents as nexus_mon_mevents
            FROM
                nexus_summary n
                JOIN journal_summary j ON n.beamline = j.beamline
                AND n.run_number = j.run_number
                JOIN icp_debug i ON i.beamline = n.beamline
                AND n.run_number = i.run_number
                JOIN beamline_target_mapping b ON n.beamline = b.beamline
            WHERE
                duration > 0.0
                AND good_frames > 0
                AND i.icp_error_count = 0
                AND j.total_mevents >= (total_detector_mevents + total_monitor_mevents)
        );

        select
            *
        from
            event_counts
        where beamline = 'NIMROD'  AND run_number = 97597;
        """
    )
    return


@app.cell
def _(event_counts, mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE events_per_frame as (
            SELECT
                beamline,
                run_number,
                target_station,
            	good_frames,
                ROUND(nexus_det_mevents / good_frames , 4) as det_mevents_per_frame,
                ROUND(nexus_mon_mevents / good_frames, 4) as mon_mevents_per_frame,
            FROM
                event_counts
        );
        -- select * from events_per_frame order by det_mevents_per_frame DESC;
        """
    )
    return


@app.cell
def _(
    ev44_header_bits,
    ev44_per_event_bits,
    events_per_frame,
    mo,
    target_station,
):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE event_data_rate as (
            SELECT
                e.beamline,
                e.run_number,
                t.mode_label,
                t.framerate_hz,
                det_mevents_per_frame,
        	    mon_mevents_per_frame,
                framerate_hz * (
                    ({ev44_header_bits} / 1_000_000) + det_mevents_per_frame * {ev44_per_event_bits}
                ) as det_mbits_sec,
                framerate_hz * (
                    ({ev44_header_bits} / 1_000_000) + mon_mevents_per_frame * {ev44_per_event_bits}
                ) as mon_mbits_sec
            FROM
                events_per_frame e
                JOIN target_station t ON e.target_station = t.target_station
        );
        """
    )
    return


@app.cell
def _(event_data_rate, mo):
    _df = mo.sql(
        f"""
        SELECT
            beamline,
            mode_label,
            ROUND(MAX(det_mevents_per_frame), 4) as max_det_mevents_per_frame,
            ROUND(MAX(mon_mevents_per_frame), 4) as max_mon_mevents_per_frame,
            ROUND(MAX(det_mbits_sec), 4) as max_det_mbits_sec,
            ROUND(MAX(mon_mbits_sec), 4) as max_mon_mbits_sec,
            ROUND(QUANTILE(det_mevents_per_frame, 0.99), 4) as p99_det_mevents_per_frame,
            ROUND(QUANTILE(mon_mevents_per_frame, 0.99), 4) as p99_mon_mevents_per_frame,
            ROUND(QUANTILE(det_mbits_sec, 0.99), 4) as p99_det_mbits_sec,
            ROUND(QUANTILE(mon_mbits_sec, 0.99), 4) as p99_mon_mbits_sec
        FROM
            event_data_rate
        GROUP BY
            beamline, mode_label
        ORDER BY beamline ASC
        """
    )
    return


if __name__ == "__main__":
    app.run()
