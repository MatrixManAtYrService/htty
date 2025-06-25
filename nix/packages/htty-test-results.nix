# Test results package - runs pytest and builds test results as artifacts
{ inputs, pkgs, ... }:

let
  # Get project metadata
  pyprojectToml = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  inherit (pyprojectToml.project) version;

  # Get the test environment from htty-test
  httyTestEnv = inputs.self.packages.${pkgs.system}.htty-test;

in
pkgs.stdenvNoCC.mkDerivation {
  pname = "htty-test-results";
  inherit version;
  
  src = pkgs.lib.cleanSource ../../tests;

  # Enable the check phase
  doCheck = true;
  
  # Use the htty test environment
  nativeBuildInputs = [ httyTestEnv ];

  buildPhase = ''
    runHook preBuild
    
    # Set up environment
    echo "🧪 Setting up test environment..."
    
    # Create writable directories
    export HOME=$TMPDIR/home
    export PYTEST_CACHE_DIR=$TMPDIR/.pytest_cache
    mkdir -p "$HOME" "$PYTEST_CACHE_DIR"
    
    # Set up Python path to find htty
    export PYTHONPATH="${httyTestEnv}/lib/python3.12/site-packages:$PYTHONPATH"
    export PATH="${httyTestEnv}/bin:$PATH"
    
    echo "Environment setup complete"
    echo "Python: $(which python)"
    echo "Pytest: $(which pytest)"
    
    runHook postBuild
  '';

  checkPhase = ''
    runHook preCheck

    echo "🧪 Running htty library tests..."
    
    # Debug: Check what files are available
    echo "📂 Available files in source:"
    find . -name "*.py" | head -10
    echo ""
    echo "📂 Contents of lib_tests directory:"
    ls -la lib_tests/ || echo "lib_tests directory not found"
    echo ""
    
    # Set up test results directories
    mkdir -p $TMPDIR/test_results
    mkdir -p $TMPDIR/test_logs

    # Test if pytest can collect tests first
    echo "🔍 Testing pytest collection..."
    ${httyTestEnv}/bin/htty-pytest --collect-only lib_tests/ 2>&1 | tee $TMPDIR/test_logs/collection.log
    echo ""

    # Run pytest with verbose output and capture results
    echo "Running pytest on lib_tests/"
    
    # Initialize test tracking variables
    export PYTEST_EXIT_CODE=0
    export PYTEST_RESULT="UNKNOWN"
    
    # Run pytest and capture both output and exit code
    if ${httyTestEnv}/bin/htty-pytest -v -s --tb=short lib_tests/ \
        --junitxml=$TMPDIR/test_results/junit.xml \
        -o cache_dir="$PYTEST_CACHE_DIR" \
        2>&1 | tee $TMPDIR/test_logs/pytest_output.log; then
      echo "✅ All tests passed!"
      export PYTEST_RESULT="PASSED"
      export PYTEST_EXIT_CODE=0
    else
      echo "❌ Some tests failed"
      export PYTEST_RESULT="FAILED"  
      export PYTEST_EXIT_CODE=$?
      echo "Exit code: $PYTEST_EXIT_CODE"
    fi

    # Count test results from the output
    TOTAL_TESTS=$(grep -E "^lib_tests.*::.*" "$TMPDIR/test_logs/pytest_output.log" | wc -l || echo "0")
    PASSED_TESTS=$(grep -E "PASSED" "$TMPDIR/test_logs/pytest_output.log" | wc -l || echo "0")
    FAILED_TESTS=$(grep -E "FAILED" "$TMPDIR/test_logs/pytest_output.log" | wc -l || echo "0")
    SKIPPED_TESTS=$(grep -E "SKIPPED" "$TMPDIR/test_logs/pytest_output.log" | wc -l || echo "0")
    
    echo ""
    echo "📊 Test Summary:"
    echo "  Total tests: $TOTAL_TESTS"
    echo "  Passed: $PASSED_TESTS"
    echo "  Failed: $FAILED_TESTS"
    echo "  Skipped: $SKIPPED_TESTS"
    echo "  Overall result: $PYTEST_RESULT"

    # Store results for installation phase
    echo "$PYTEST_RESULT" > $TMPDIR/test_results/overall_result.txt
    echo "$PYTEST_EXIT_CODE" > $TMPDIR/test_results/exit_code.txt
    echo "$TOTAL_TESTS" > $TMPDIR/test_results/total_tests.txt
    echo "$PASSED_TESTS" > $TMPDIR/test_results/passed_tests.txt
    echo "$FAILED_TESTS" > $TMPDIR/test_results/failed_tests.txt
    echo "$SKIPPED_TESTS" > $TMPDIR/test_results/skipped_tests.txt

    # Even if tests fail, we want to capture the results
    # So we don't exit 1 here - we build the results artifact
    
    runHook postCheck
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out

    # Install test result files
    echo "📁 Installing test results..."
    
    # Copy all test results
    cp -r $TMPDIR/test_results/* $out/
    
    # Copy test logs
    mkdir -p $out/logs
    cp $TMPDIR/test_logs/* $out/logs/
    
    # Create a human-readable summary
    cat > $out/test_summary.txt << EOF
htty Library Test Results
========================

Overall Result: $(cat $out/overall_result.txt)
Exit Code: $(cat $out/exit_code.txt)

Test Counts:
- Total: $(cat $out/total_tests.txt)
- Passed: $(cat $out/passed_tests.txt)  
- Failed: $(cat $out/failed_tests.txt)
- Skipped: $(cat $out/skipped_tests.txt)

Generated: $(date)
Environment: ${httyTestEnv}

Full logs available in logs/pytest_output.log
JUnit XML available in junit.xml
EOF

    # Create a status indicator file
    if [ "$(cat $out/overall_result.txt)" = "PASSED" ]; then
      touch $out/SUCCESS
      echo "✅ All tests passed - created SUCCESS marker"
    else
      touch $out/FAILURE
      echo "❌ Tests failed - created FAILURE marker"
    fi
    
    # Display final summary
    echo ""
    echo "📋 Final Test Results Summary:"
    cat $out/test_summary.txt
    
    runHook postInstall
  '';

  # Always succeed the derivation build, even if tests fail
  # The test results are captured in the output files
  meta = with pkgs.lib; {
    description = "htty library test results";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
  };
}
