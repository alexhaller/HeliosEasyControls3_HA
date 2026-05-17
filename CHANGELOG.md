## [1.8.7](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.6...v1.8.7) (2026-05-17)

### Bug Fixes

* correct buffer offsets for CO2 and RH limits ([40fdb64](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/40fdb640c3f4c38dd3ca7eb5eaad71d01e076246))

## [1.8.6](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.5...v1.8.6) (2026-05-17)

### Bug Fixes

* expand debug log to dump full settings buffer range ([c0fd0c5](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/c0fd0c59e631373e94d1119c7053e69577dc5549))

## [1.8.5](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.4...v1.8.5) (2026-05-17)

### Bug Fixes

* clean up entities, fix label errors and sensor detection ([a1ee8ba](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/a1ee8bab136774019efe8c2c895a2eea302da593))

## [1.8.4](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.3...v1.8.4) (2026-05-16)

### Bug Fixes

* add icon.png to component root for HA integrations page ([d94f548](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/d94f548f2a61421fd2cf47bfca192db00a3dc6da))

## [1.8.3](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.2...v1.8.3) (2026-05-16)

### Bug Fixes

* remove HA suffix from integration display name ([e504df9](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/e504df977062ed12c8a67cb734b362c674f071c9))

## [1.8.2](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.1...v1.8.2) (2026-05-14)

### Bug Fixes

* enforce already_configured guard and use _attr_icon in binary sensors ([4392685](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/439268563418426a40ae83bc5fa725db9fd4299c))

### Documentation

* move general conventions to global ~/.claude/CLAUDE.md ([6fa61a9](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/6fa61a997fbd100e74c18d862254549f6e7585d1))
* trim project CLAUDE.md removing notes now covered by global config ([603f1e6](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/603f1e6720daa0cb6920107a4c330c2988d6c682))

### Code Refactoring

* **device:** extract protocol constants and split _parseData into focused methods ([5c20375](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/5c2037547a70f625523428863a6c0a117f97c9a0))

## [1.8.1](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.8.0...v1.8.1) (2026-05-14)

### Bug Fixes

* restore brand/icon.png inside integration for HACS validation ([c94966e](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/c94966e1ed1db41f5c883feb2377897e9582d222))

### Documentation

* correct brand asset paths in CLAUDE.md ([1534e29](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/1534e29e804aae26e2659a78467a0bff661f847e))

## [1.8.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.7.0...v1.8.0) (2026-05-14)

### Features

* HA conventions compliance and HACS publishing setup ([3be12d9](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/3be12d9ce808b1594faff828b85da744d0ee3108))

### Documentation

* clarify semantic-release owns manifest.json version ([d21c97e](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/d21c97ebef06d913ae8b6888a0ef7118a4ac5168))
* comprehensive register map with full Vallox API cross-reference ([48f97cd](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/48f97cd9afbd40790516b4992dca639de5b98705))
* rewrite README with current entity list and full register map ([6731561](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/67315612ad659adad4dc8bd5905c8ce0cc5d9c8e))

## [1.7.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.6.0...v1.7.0) (2026-05-12)

### Features

* categorize entities, rename Individual/Intensive, add new settings ([6c3b42a](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/6c3b42a9f1f8edc512d4c44433b070893fd8cc43))

## [1.6.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.5.0...v1.6.0) (2026-05-12)

### Features

* replace placeholder with fan ventilation icon ([53e3ec0](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/53e3ec0fdfd4fb43c2330b4ffedf5f0131a78053))

## [1.5.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.4.2...v1.5.0) (2026-05-12)

### Features

* add brand icon placeholder (256x256) ([d297c97](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/d297c9741a7591ca361d4e7f6ed007b21660375a))

## [1.4.2](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.4.1...v1.4.2) (2026-05-12)

### Bug Fixes

* sort manifest.json keys per hassfest requirements ([f26d40c](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/f26d40c89bd6765e3cc4ad8dc73ab8b5daadd778))

## [1.4.1](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.4.0...v1.4.1) (2026-05-12)

### Bug Fixes

* resolve CI validation errors ([cf811af](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/cf811afc5511e15afb438b3698237557bb70cb5c))

## [1.4.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.3.0...v1.4.0) (2026-05-11)

### Features

* add extended sensor data from Vallox register map ([cc156a2](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/cc156a246e247f4bbaf74f87348a3940172dc325))
* add full write control and remaining read values ([7f4b692](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/7f4b6924d7e18c3d6bf9e916a4ed7d1be930964b))
* add remaining timers, cell temp, RH/CO2 control switches ([79e2dea](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/79e2dead0b3651924c096257d05b49bfaee65c67))

### Code Refactoring

* fix duration reads, extract write-response helper, remove duplicate sensors ([b888388](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/b888388c3e25ebe0cc5c009905a7f458bd5eef91))
* improve code quality across integration ([c86daae](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/c86daae82a6adf15b41bcbbdb3e09ad8ea1dab73))

## [1.3.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.2.0...v1.3.0) (2026-03-28)

### Features

* New sensor "Heat recovery efficiency" ([869da31](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/869da3114853d6787dbd046a0a8eef797ffd6ec0))

## [1.2.0](https://github.com/alexhaller/HeliosEasyControls3_HA/compare/v1.1.0...v1.2.0) (2026-03-28)

### Features

* Added GitHub Action ([4ac482d](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/4ac482d55b6cf0da56b6eb82414bbb6abf2fb9e5))
* rework, GitHub Action, simplification ([59e49ab](https://github.com/alexhaller/HeliosEasyControls3_HA/commit/59e49abe0f4e402e13646f9bd49af0eb2270868b))
