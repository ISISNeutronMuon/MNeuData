# ISIS Journal files

Each file from the beamline sibdirectories of <http://journals.isis.cclrc.ac.uk/jv/>
describes a cycle's worth of runs on that beamline.

An `<NXEntry name="INSTXXXXXXXX">` element describes a single run where the `name` attribute captures
the instrument name concatenated with a zero-padded run number.
This does not necessarily match the filename stem for the NeXus or raw files.

A short description of fields used from the ISIS journal files
