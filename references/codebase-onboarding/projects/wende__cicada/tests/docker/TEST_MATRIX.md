# SCIP Language Test Matrix

This document shows expected test results in clean Docker environments.

## Test Environments

### Base Environment (Dockerfile.base)
- ✅ Python 3.11
- ✅ Git
- ✅ uv
- ✅ Cicada installed
- ❌ No language runtimes
- ❌ No SCIP indexers
- ❌ No build tools

## Expected Results in Base Environment

All languages should **FAIL** with clear error messages:

| Language | Expected Error | Missing Dependencies |
|----------|---------------|---------------------|
| **Go** | `[Errno 2] No such file or directory: 'scip-go'` | • `golang-go`<br>• `scip-go` |
| **Java** | `scip-java not found. Install via: brew install coursier/formulas/coursier` | • `openjdk-17-jdk`<br>• `coursier` |
| **Scala** | `scip-java not found...` + `No sbt version detected` | • `openjdk-17-jdk`<br>• `sbt`<br>• `coursier` |
| **Ruby** | `[Errno 2] No such file or directory: 'scip-ruby'` | • `ruby`<br>• `scip-ruby` |
| **Dart** | `dart command not found. Install Dart SDK: https://dart.dev/get-dart` | • Dart SDK<br>• `scip_dart` (via pub global) |
| **C** | `[Errno 2] No such file or directory: 'scip-clang'` | • `build-essential`<br>• `scip-clang` |
| **C++** | `[Errno 2] No such file or directory: 'scip-clang'` | • `build-essential`<br>• `cmake`<br>• `scip-clang` |
| **C#** | `[Errno 2] No such file or directory: 'scip-dotnet'` | • .NET SDK<br>• `scip-dotnet` |
| **VB** | `[Errno 2] No such file or directory: 'scip-dotnet'` | • .NET SDK<br>• `scip-dotnet` |

## Per-Language Complete Environments

### Go (Dockerfile.go)
```dockerfile
FROM cicada-base
RUN apt-get install golang-go
RUN go install github.com/sourcegraph/scip-go@latest
```
**Result:** ✅ Should pass

### Java (Dockerfile.java)
```dockerfile
FROM cicada-base
RUN apt-get install openjdk-17-jdk
RUN curl -fL ... > /usr/local/bin/cs
```
**Result:** ✅ Should pass (uses coursier fallback)

### Scala (Dockerfile.scala)
```dockerfile
FROM cicada-base
RUN apt-get install openjdk-17-jdk sbt
RUN curl -fL ... > /usr/local/bin/cs
```
**Result:** ✅ Should pass

### Ruby (Dockerfile.ruby)
```dockerfile
FROM cicada-base
RUN apt-get install ruby ruby-dev build-essential
RUN curl -L scip-ruby-linux-amd64 > /usr/local/bin/scip-ruby
```
**Result:** ✅ Should pass

### Dart (Dockerfile.dart)
```dockerfile
FROM cicada-base
RUN wget dart_stable && apt-get install dart
RUN dart pub global activate scip
```
**Result:** ✅ Should pass (auto-runs dart pub get)

### C (Dockerfile.c)
```dockerfile
FROM cicada-base
RUN apt-get install build-essential cmake
RUN wget scip-clang-linux-amd64 > /usr/local/bin/scip-clang
```
**Result:** ✅ Should pass

### C++ (Dockerfile.c)
Same as C
**Result:** ✅ Should pass

### C# (Dockerfile.dotnet)
```dockerfile
FROM cicada-base
RUN dotnet-install.sh --channel 8.0
RUN dotnet tool install --global scip-dotnet
```
**Result:** ✅ Should pass

### VB (Dockerfile.dotnet)
Same as C#
**Result:** ✅ Should pass

## Test Commands

### Test Base Environment (expect all failures)
```bash
cd tests/docker
./test-all-languages.sh
```

Expected output: 9/9 failures with clear error messages

### Test Individual Language (expect success)
```bash
docker build -t cicada-go -f Dockerfile.go ../..
docker run cicada-go
```

Expected output: "✅ Go indexing successful"

### Test All Complete Environments
```bash
for lang in go java scala ruby dart c dotnet; do
  docker build -t cicada-$lang -f Dockerfile.$lang ../..
done
```

Expected output: All builds succeed, all tests pass

## Success Criteria

### For Base Environment Tests
- ✅ Each language fails with specific tool missing
- ✅ Error message includes tool name
- ✅ Error message includes installation hint
- ❌ No generic Python stack traces
- ❌ No "Unknown error" messages

### For Complete Environment Tests
- ✅ All 9 languages index successfully
- ✅ Each produces "Indexed X files" output
- ✅ No errors or warnings (except known Ruby warnings)

## What This Tests

1. **Error Message Quality** - Are our missing dependency messages helpful?
2. **Installation Guidance** - Do we point users to the right place?
3. **Auto-Setup Features** - Do coursier fallback and dart pub get work?
4. **Minimal Requirements** - What's the smallest set of deps needed?
5. **Dockerfile Documentation** - Can users copy our Dockerfiles as setup guides?

## Future Improvements

Based on test results, we should:
1. Add pre-flight checks that test for required tools before attempting index
2. Improve error messages to be more actionable
3. Create installation scripts for each platform
4. Document Docker setup as official deployment method
