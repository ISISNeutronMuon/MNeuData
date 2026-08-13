# ISIS Journal files

Each file from the beamline subdirectories of <http://journals.isis.cclrc.ac.uk/jv/>
describes a cycle's worth of runs on that beamline.

An `<NXEntry name="INSTXXXXXXXX">` element describes a single run where the `name` attribute captures
the instrument name concatenated with a zero-padded run number.
This does not necessarily match the filename stem for the NeXus or raw files.

The following sections provide descriptions for the fields:

## frame_sync

Defines the timing mode of the beamline for this run, i.e. how many pulses/second
will it see.

The [known values](https://github.com/ISISNeutronMuon/ISISICP/blob/949884f43d6241736af2553de970d2b9cc0bf800/newicp/isiscrpt_types.h#L10) are:

- `ISIS`: Nominal framerate depends on the target station.
  - `TS1`: 40Hz nomically, but can be 50Hz if beam configured to run to TS1 only
  - `TS2`: 10Hz
- `ISISTS1Only`: 40Hz or 50Hz if beam configured send all pulses to TS1.
- `ISISFirstPulse`: First TS1 pulse=10Hz
- `SMP`: Timing is based on the chopper frequency. The chopper logs will capture this
  but there is no consistent naming of what chopper is being used here.
- `InternalTest50Hz`: An internal test clock, mostly used for quiet counts type of run.

If capturing in event mode then looking at the time between frames in `framelog/raw_frame_log` will give
this information.
