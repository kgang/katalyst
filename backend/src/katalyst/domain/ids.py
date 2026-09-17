"""The identifiers the rules layer passes around, and the one thing it believes about them.

An identifier here is a plain string. This layer never checks its format, because
it honestly cannot: a well-formed identifier is minted with a clock and a source
of randomness, and this layer reads neither (decision record 0003). Minting lives
outside, in `katalyst.engine.ids`, and the finished string is passed in as an
ordinary value.

What this layer does check is the only thing it can see from inside one map: that
an identifier an arrow names is present on that same map, and that the map's
starting claim is one of the claims on it. Those checks live with the rest of the
map's validity rules, not here.

Three separate names for the same underlying string costs nothing at runtime and
makes a signature readable: a function taking a `LinkId` is plainly not the one
taking a `PropositionId`, even though both are strings.
"""

PropositionId = str
"""The identifier of one claim, unique within its map.

Our code mints it and the model never invents one. Stored examples use readable
ones — `H`, `C`, `B`, `R`, `S`, `M1`, `M2`, `N1` — which is possible precisely
because nothing here checks the format.
"""

LinkId = str
"""The identifier of one arrow, unique within its map. Minted by our code."""

BranchId = str
"""The identifier of one branch: a named, ordered list of edits. Minted by our code."""
