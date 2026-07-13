# Dependency Audit

This audit covers the `plugin.video.nlziet` dependencies declared in `addon.xml`.
The goal is to keep only dependencies required directly by this add-on and let
Kodi resolve transitive dependencies from the packages that own them.

## Dependency Graph

```text
plugin.video.nlziet
├── xbmc.python
├── script.module.requests
│   ├── script.module.certifi
│   ├── script.module.chardet
│   ├── script.module.idna
│   └── script.module.urllib3
├── script.module.backports.zoneinfo
│   └── script.module.tzdata
├── script.module.inputstreamhelper
│   └── script.module.pysocks
└── inputstream.adaptive
```

`script.module.charset-normalizer` is not in the graph. It is not imported by
this add-on, is not declared by Kodi's `script.module.requests` package, and is
not available in the Kodi Nexus or Omega add-on repositories checked during this
audit.

## Direct And Indirect Dependencies

| Dependency | Declared before audit | Directly imported | Indirect only | Required | Reason | Recommended action |
| --- | --- | --- | --- | --- | --- | --- |
| `xbmc.python` | Yes | Runtime ABI, not a Python import | No | Yes | Required Kodi Python extension dependency for Python 3 add-ons. | Keep. |
| `script.module.requests` | Yes | Yes | No | Yes | `resources/lib/nlziet_api.py` imports `requests` directly and uses it for API calls. | Keep. |
| `script.module.certifi` | Yes | No | Yes, through `script.module.requests` | No direct declaration needed | Kodi's `script.module.requests` package declares `script.module.certifi`; this add-on does not import `certifi`. | Remove direct declaration. |
| `script.module.charset-normalizer` | Yes | No | No | No | No source import was found, Kodi's `script.module.requests` package does not declare it, and Kodi Nexus/Omega repositories do not provide this add-on id. | Remove. |
| `script.module.backports.zoneinfo` | Yes | Yes, fallback only | No | Conditional | `default.py`, `resources/lib/iptvmgr.py`, and `resources/lib/controllers/browse_controller.py` import stdlib `zoneinfo` first and fall back to `backports.zoneinfo`. | Keep. |
| `script.module.tzdata` | Yes | No | Yes, through `script.module.backports.zoneinfo` | No direct declaration needed | The `backports.zoneinfo` Kodi package declares `script.module.tzdata`; this add-on does not import `tzdata`. | Remove direct declaration. |
| `script.module.inputstreamhelper` | Yes | Yes | No | Yes | `default.py` imports `inputstreamhelper` before DRM playback to verify InputStream Adaptive and Widevine readiness. | Keep. |
| `inputstream.adaptive` | Yes | No Python import | No | Yes for DRM playback | Playback code sets `inputstream.adaptive` properties and requires the binary add-on for MPEG-DASH/Widevine playback. | Keep. |

## Kodi Repository Compatibility Notes

The Nexus and Omega repository indexes were checked against Kodi's published
add-on mirrors. The following declared dependencies are available as installable
Kodi add-ons: `script.module.requests`, `script.module.certifi`,
`script.module.backports.zoneinfo`, `script.module.tzdata`, and
`script.module.inputstreamhelper`.

`inputstream.adaptive` is published as a platform-specific binary add-on in the
Kodi repository ecosystem and is listed by Kodi's Omega add-on catalog. The
direct dependency remains because NLZiet DRM playback configures and requires
InputStream Adaptive at runtime.

`script.module.charset-normalizer` was not present in the Nexus or Omega
repository indexes. Keeping it in `addon.xml` makes clean installations fail
before Kodi can install the actual add-on.

## Removed Dependencies

`script.module.certifi` was removed because it is a transitive dependency of
Kodi's `script.module.requests` package.

`script.module.charset-normalizer` was removed because it is not imported, not
declared by Kodi's `requests` package, and unavailable from the checked Kodi
repositories.

`script.module.tzdata` was removed because it is a transitive dependency of
Kodi's `script.module.backports.zoneinfo` package.
