# ISIS archive

A collection of notes regarding the ISIS archive.

The archive is replicated between 3 locations and each can be accessed at the following urls:

- R80: isisdatar80.isis.cclrc.uk
- R55: isisdatar55.isis.cclrc.uk
- R3: isisdatar3.isis.cclrc.uk

Each beamline is shared via a Windows share at `\\{url}\NDX{beamline}$`.
[DFS](https://learn.microsoft.com/en-us/windows-server/storage/dfs-namespaces/dfs-overview?tabs=server-manager) allows a single share, `\\isis.cclrc.ac.uk\inst$`,
to redirect to the above physical locations silently to allow for transparent failover.
