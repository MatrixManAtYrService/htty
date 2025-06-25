# Test environment that combines htty-pylib with test-specific dependencies
{ inputs, pkgs, ... }:

let
  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Get the clean htty Python library environment
  httyPylib = inputs.self.packages.${pkgs.system}.htty-pylib;

  # Load the test workspace (pytest and other test tools)
  testWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../../test-env;
  };

  # Create python set with just the test dependencies (no htty - we'll get that from htty-pylib)
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python3;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (testWorkspace.mkPyprojectOverlay { 
        sourcePreference = "wheel";
      })
    ]
  );

  # Build environment with just test dependencies (pytest, etc.)
  testDepsEnv = pythonSet.mkVirtualEnv "test-deps-env" (
    # Remove htty from the dependencies since we'll get it from htty-pylib
    builtins.removeAttrs testWorkspace.deps.default [ "htty" ]
  );

in
pkgs.stdenvNoCC.mkDerivation {
  pname = "htty-test";
  inherit version;
  
  src = pkgs.writeText "dummy" "";
  dontUnpack = true;
  
  buildInputs = [ testDepsEnv httyPylib ];

  installPhase = ''
    mkdir -p $out/bin
    
    # Create test runner that combines both environments
    cat > $out/bin/htty-test << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Testing htty library with test environment..."

# Set up Python path to include both environments
# Note: Using lib/python3.12/site-packages as a reasonable default path
export PYTHONPATH="${httyPylib}/lib/python3.12/site-packages:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"

# Set up PATH to include htty-pylib binaries (where ht is located)
export PATH="${httyPylib}/bin:${testDepsEnv}/bin:$PATH"

# Use python from test environment but with htty available via PYTHONPATH
PYTHON="${testDepsEnv}/bin/python"

# Test basic functionality
echo "Testing htty import and basic functionality..."
$PYTHON -c "
import htty
print('✅ htty import successful')
print('Version:', htty.__version__)

# Test basic functionality
try:
    proc = htty.run(['echo', 'Hello from test environment'], rows=3, cols=20)
    snapshot = proc.snapshot()
    proc.exit()
    print('✅ Basic htty functionality working')
    print('Output:', repr(snapshot.text.strip()))
except Exception as e:
    print('❌ htty functionality failed:', e)
    exit(1)

# Test ht binary discovery
from htty import find_ht_bin
try:
    ht_path = find_ht_bin()
    print('✅ ht binary found at:', ht_path)
except Exception as e:
    print('❌ ht binary not found:', e)
    exit(1)
"

echo ""
echo "🎉 All tests passed!"
echo ""
echo "Environment details:"
echo "  Python: $PYTHON"
echo "  Pytest: ${testDepsEnv}/bin/pytest (available via PATH)"
echo "  htty-pylib: ${httyPylib}"
echo "  test-deps: ${testDepsEnv}"
EOF
    chmod +x $out/bin/htty-test

    # Create pytest runner that combines both environments
    cat > $out/bin/htty-pytest << 'EOF'
#!/usr/bin/env bash
# Run pytest with htty available
export PYTHONPATH="${httyPylib}/lib/python3.12/site-packages:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"
export PATH="${httyPylib}/bin:${testDepsEnv}/bin:$PATH"
exec "${testDepsEnv}/bin/pytest" "$@"
EOF
    chmod +x $out/bin/htty-pytest

    # Create python shell with combined environment
    cat > $out/bin/htty-test-python << 'EOF'
#!/usr/bin/env bash
# Python shell with htty + test tools available
export PYTHONPATH="${httyPylib}/lib/python3.12/site-packages:${testDepsEnv}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"
export PATH="${httyPylib}/bin:${testDepsEnv}/bin:$PATH"
exec "${testDepsEnv}/bin/python" "$@"
EOF
    chmod +x $out/bin/htty-test-python
  '';

  meta = with pkgs.lib; {
    description = "Test environment combining htty-pylib with test-specific dependencies";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    mainProgram = "htty-test";
  };
}
