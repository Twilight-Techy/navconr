# Local release candidate and publication gates

Build locally with `python scripts/release.py` from the development environment. The script builds the inspector, copies its static output into the package, builds the wheel/source distribution, and records artifact hashes in `reports/release-artifacts.json`. It never uploads artifacts or selects a distribution license.

Verify a candidate in an isolated environment by installing the wheel, running `navconr --version`, ingesting a temporary corpus, querying it, and serving the bundled inspector from outside the source checkout. Optional extras should not be required for Markdown/lexical use. Format/search/MCP workflows need their declared extras.

The current version is `0.1.0rc1`. The GitHub source repository is https://github.com/Twilight-Techy/navconr. Package-registry identity and distribution license remain unresolved. The user authorized public source publication; this does not select an open-source license or publish a registry release. External publishing and paper submission need concrete destinations, appropriate account access, and the user's applicable authorization. Real-model checks are separately deferred by the user.

Required remaining research gates include independently reviewed annotations, stronger semantic/model baselines, compatible external-method runs, common-reader answer evaluation, final claim/protocol freeze, and clean independent reproduction. A software smoke report and manuscript draft do not complete these gates.

The local readiness report should list actual checks and their evidence. Unrun environments or provider combinations remain unverified. When publication is authorized and all chosen release gates pass, publish the exact hashed artifacts, verify installation from the public registry, and record URLs/versions in memory. Rollback/replacement follows the selected registry's rules; do not overwrite immutable released artifacts.
