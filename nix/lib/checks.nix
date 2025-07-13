# Code analysis utilities for htty
pkgs:
let
  inherit (pkgs) lib;

  # Create a check script that runs in current directory
  makeCheck = args:
    let
      name = args.name or (throw "makeCheck: 'name' is required");
      description = args.description or name;
      dependencies = args.dependencies or [ ];
      command = args.command or (throw "makeCheck: 'command' is required");
      verboseCommand = args.verboseCommand or command;

      # Basic environment setup
      environment = {
        LANG = "en_US.UTF-8";
        LC_ALL = "en_US.UTF-8";
        PYTHONIOENCODING = "utf-8";
      } // (args.environment or { });

      # Resolve dependencies with basic tools
      resolvedDeps = dependencies ++ (with pkgs; [ coreutils ]);
    in
    {
      inherit name description command verboseCommand;
      scriptContent = ''
        # Set up environment variables
        ${lib.concatStringsSep "\n" (lib.mapAttrsToList (k: v: "export ${k}=${lib.escapeShellArg (toString v)}") environment)}

        # Add dependencies to PATH
        export PATH="${lib.concatStringsSep ":" (map (dep: "${dep}/bin") resolvedDeps)}:$PATH"

        # Run the appropriate command based on verbose mode
        if [ "$verbose" = "true" ]; then
          ${verboseCommand}
        else
          ${command}
        fi
      '';
    };

  # Generate a script that runs multiple checks
  generateAnalysisScript =
    { name
    , description ? "Code analysis"
    , checks ? { }
    }:
    let
      checkScripts = builtins.concatStringsSep "\n\n" (
        builtins.attrValues (builtins.mapAttrs
          (checkName: check: ''
            # ============================================================================
            # CHECK: ${checkName}
            # Description: ${check.description}
            # ============================================================================
            echo "================================================"
            echo "[${checkName}] ${check.description}"
            echo "================================================"

            # Start timing
            start_time=''$(python3 -c "import time; print(f'{time.time():.3f}')" 2>/dev/null || date +%s.%N)

            # Execute the check script
            ${check.scriptContent}
            check_exit_code=$?

            # Calculate timing
            end_time=''$(python3 -c "import time; print(f'{time.time():.3f}')" 2>/dev/null || date +%s.%N)
            if command -v python3 >/dev/null 2>&1; then
              duration=''$(python3 -c "print(f'{float(\"''$end_time\") - float(\"''$start_time\"):.3f}s')" 2>/dev/null)
            else
              duration="''$(echo "''$end_time - ''$start_time" | bc 2>/dev/null || echo "unknown")s"
            fi

            # Report result
            if [ $check_exit_code -eq 0 ]; then
              echo "✅ ${check.description} - PASSED ($duration)"
            else
              echo "❌ ${check.description} - FAILED ($duration)"
              if [ -z "''${FAILED_CHECKS:-}" ]; then
                FAILED_CHECKS="${checkName}"
              else
                FAILED_CHECKS="''$FAILED_CHECKS,${checkName}"
              fi
            fi
          '')
          checks)
      );
    in
    ''
      set -euo pipefail

      verbose=false
      while getopts "v" opt; do
        case ''${opt} in
          v ) verbose=true;;
          \? ) echo "Usage: $0 [-v]"
               exit 1;;
        esac
      done

      export verbose

      # Initialize failed checks tracker
      FAILED_CHECKS=""

      echo "🔍 Running ${description}..."
      echo ""

      ${checkScripts}

      echo "================================================"
      if [ -z "$FAILED_CHECKS" ]; then
        echo "🎉 All ${description} checks passed!"
      else
        echo "❌ Some checks failed: $FAILED_CHECKS"
        exit 1
      fi
    '';

  # Create a runnable script package
  createAnalysisPackage = args:
    let
      scriptText = generateAnalysisScript args;
    in
    pkgs.writeShellScriptBin args.name scriptText;

  # Individual check definitions (similar to checkdef but simpler)
  deadnixCheck = makeCheck {
    name = "deadnix";
    description = "Nix dead code analysis";
    dependencies = with pkgs; [ deadnix ];
    command = "deadnix -q .";
    verboseCommand = "deadnix .";
  };

  nixpkgsFmtCheck = makeCheck {
    name = "nixpkgs-fmt";
    description = "Nix file formatting";
    dependencies = with pkgs; [ nixpkgs-fmt ];
    command = ''find . -name "*.nix" -not -path "./.*" -not -path "./result*" -exec nixpkgs-fmt {} \;'';
    verboseCommand = ''find . -name "*.nix" -not -path "./.*" -not -path "./result*" -exec nixpkgs-fmt {} \;'';
  };

  statixCheck = makeCheck {
    name = "statix";
    description = "Nix static analysis";
    dependencies = with pkgs; [ statix ];
    command = "statix check .";
    verboseCommand = "statix check .";
  };

  ruffCheckCheck = makeCheck {
    name = "ruff-check";
    description = "Python linting with ruff (auto-fix enabled)";
    dependencies = with pkgs; [ ruff ];
    command = "ruff check --fix --unsafe-fixes";
    verboseCommand = "ruff check --fix --unsafe-fixes --verbose";
  };

  ruffFormatCheck = makeCheck {
    name = "ruff-format";
    description = "Python formatting with ruff";
    dependencies = with pkgs; [ ruff ];
    command = "ruff format";
    verboseCommand = "ruff format --verbose";
  };

  trimWhitespaceCheck = makeCheck {
    name = "trim-whitespace";
    description = "Remove trailing whitespace";
    dependencies = with pkgs; [ ripgrep gnused findutils ];
    command = ''
      echo "Checking for trailing whitespace in current directory..."

      # Use ripgrep to find files with trailing whitespace
      if files_with_whitespace=$(rg --files-with-matches --no-ignore --glob '*.py' --glob '*.nix' --glob '*.md' --glob '*.txt' --glob '*.yml' --glob '*.yaml' '[[:space:]]$' 2>/dev/null) && [ -n "$files_with_whitespace" ]; then
        # Check if we can write to the current directory
        if [ -w "." ]; then
          echo "Found files with trailing whitespace, trimming..."
          printf '%s\n' "$files_with_whitespace" | xargs -P4 -I {} ${pkgs.gnused}/bin/sed -i 's/[[:space:]]*$//' {}
          echo "✅ Trailing whitespace trimmed"
        else
          echo "❌ Found files with trailing whitespace (read-only environment, cannot fix):"
          printf '%s\n' "$files_with_whitespace"
          echo ""
          echo "💡 Run this check in a writable directory to automatically fix trailing whitespace"
          exit 1
        fi
      else
        echo "✅ No trailing whitespace found"
      fi
    '';
    verboseCommand = ''
      printf '%s\n' "🔧 Finding files matching patterns: *.py *.nix *.md *.txt *.yml *.yaml"
      printf '%s\n' "🔧 Working in current directory: $(pwd)"
      printf '%s\n' "🔧 Using ripgrep to find files with trailing whitespace..."

      # Use ripgrep to find files with trailing whitespace
      if files_with_whitespace=$(rg --files-with-matches --no-ignore --glob '*.py' --glob '*.nix' --glob '*.md' --glob '*.txt' --glob '*.yml' --glob '*.yaml' '[[:space:]]$' 2>/dev/null) && [ -n "$files_with_whitespace" ]; then
        # Check if we can write to the current directory
        if [ -w "." ]; then
          printf '%s\n' "🔧 Found files with trailing whitespace, trimming..."
          printf '%s\n' "$files_with_whitespace" | xargs -P4 -I {} ${pkgs.gnused}/bin/sed -i 's/[[:space:]]*$//' {}
          echo "✅ Trailing whitespace trimmed"
        else
          echo "❌ Found files with trailing whitespace (read-only environment, cannot fix):"
          printf '%s\n' "$files_with_whitespace"
          echo ""
          echo "💡 Run this check in a writable directory to automatically fix trailing whitespace"
          exit 1
        fi
      else
        echo "✅ No trailing whitespace found"
      fi
    '';
  };

  pyrightCheck = makeCheck {
    name = "pyright";
    description = "Python type checking with pyright";
    dependencies = with pkgs; [ pyright ];
    command = "nix develop .#pytest-htty --command pyright";
    verboseCommand = "nix develop .#pytest-htty --command pyright --verbose";
  };

  rustClippyCheck = makeCheck {
    name = "rust-clippy";
    description = "Rust linting with clippy";
    dependencies = with pkgs; [ rustc cargo clippy ];
    command = "cd htty-core && cargo clippy --all-targets --all-features";
    verboseCommand = "cd htty-core && cargo clippy --all-targets --all-features --verbose";
  };

  # Function to create generateConstantsCheck that accesses the flake's constants
  makeGenerateConstantsCheck = { flake, files ? [ ] }:
    let
      lib = flake.lib pkgs;
      inherit (lib) constants;
      filesStr = builtins.concatStringsSep " " files;
    in
    makeCheck {
      name = "generate-constants";
      description = "Generate constants files using Cog from nix/lib/constants.nix";
      dependencies = with pkgs; [ python3 python3Packages.cogapp ];
      environment = {
        # Export constants as environment variables for Cog
        # Terminal configuration
        HTTY_DEFAULT_COLS = toString constants.terminal.default_cols;
        HTTY_DEFAULT_ROWS = toString constants.terminal.default_rows;

        # Timing constants (in milliseconds)
        HTTY_DEFAULT_SLEEP_AFTER_KEYS_MS = toString constants.timing.default_sleep_after_keys_ms;
        HTTY_SUBPROCESS_EXIT_DETECTION_DELAY_MS = toString constants.timing.subprocess_exit_detection_delay_ms;
        HTTY_COORDINATION_DELAY_MS = toString constants.timing.coordination_delay_ms;
        HTTY_GENERAL_SLEEP_INTERVAL_MS = toString constants.timing.general_sleep_interval_ms;
        HTTY_DEFAULT_SUBPROCESS_WAIT_TIMEOUT_MS = toString constants.timing.default_subprocess_wait_timeout_ms;
        HTTY_DEFAULT_SNAPSHOT_TIMEOUT_MS = toString constants.timing.default_snapshot_timeout_ms;
        HTTY_DEFAULT_EXIT_TIMEOUT_MS = toString constants.timing.default_exit_timeout_ms;
        HTTY_DEFAULT_GRACEFUL_TERMINATION_TIMEOUT_MS = toString constants.timing.default_graceful_termination_timeout_ms;
        HTTY_DEFAULT_EXPECT_TIMEOUT_MS = toString constants.timing.default_expect_timeout_ms;
        HTTY_SNAPSHOT_RETRY_TIMEOUT_MS = toString constants.timing.snapshot_retry_timeout_ms;
        HTTY_SUBSCRIPTION_TIMEOUT_MS = toString constants.timing.subscription_timeout_ms;
        HTTY_EMPTINESS_CHECK_INTERVAL_MS = toString constants.timing.emptiness_check_interval_ms;
        HTTY_FIFO_MONITORING_INTERVAL_MS = toString constants.timing.fifo_monitoring_interval_ms;
        HTTY_PTY_HEARTBEAT_INTERVAL_MS = toString constants.timing.pty_heartbeat_interval_ms;
        HTTY_HEARTBEAT_CHECK_DELAY_MS = toString constants.timing.heartbeat_check_delay_ms;
        HTTY_COMMAND_CHANNEL_CHECK_DELAY_MS = toString constants.timing.command_channel_check_delay_ms;

        # Buffer sizes and limits
        HTTY_READ_BUF_SIZE = toString constants.buffers.read_buf_size;
        HTTY_CHANNEL_BUFFER_SIZE = toString constants.buffers.channel_buffer_size;
        HTTY_SINGLE_SLOT_CHANNEL_SIZE = toString constants.buffers.single_slot_channel_size;
        HTTY_BROADCAST_CHANNEL_SIZE = toString constants.buffers.broadcast_channel_size;

        # Retry counts and thresholds
        HTTY_MAX_SNAPSHOT_RETRIES = toString constants.limits.max_snapshot_retries;
      };
      command = ''
        echo "Generating constants files using Cog from nix/lib/constants.nix..."

        # Check if we can write to the current directory
        if [ ! -w "." ]; then
          echo "❌ Cannot generate constants (read-only environment)"
          echo "💡 Run this check in a writable directory"
          exit 1
        fi

        # Files to process
        files="${filesStr}"
        files_processed=0

        for file in $files; do
          if [ -f "$file" ]; then
            echo "Processing $file..."
            cog -r "$file"
            files_processed=$((files_processed + 1))
          else
            echo "⚠️  File not found: $file"
          fi
        done

        if [ $files_processed -eq 0 ]; then
          echo "❌ No files were processed successfully"
          exit 1
        else
          echo "✅ Processed $files_processed file(s) successfully"
        fi
      '';
      verboseCommand = ''
        printf '%s\n' "🔧 Generating constants files using Cog from nix/lib/constants.nix"
        printf '%s\n' "🔧 Working in current directory: $(pwd)"
        printf '%s\n' "🔧 Environment variables:"
        printf '%s\n' "   HTTY_DEFAULT_COLS=$HTTY_DEFAULT_COLS"
        printf '%s\n' "   HTTY_DEFAULT_ROWS=$HTTY_DEFAULT_ROWS"
        printf '%s\n' "🔧 Files to process: ${filesStr}"

        # Check if we can write to the current directory
        if [ ! -w "." ]; then
          echo "❌ Cannot generate constants (read-only environment)"
          echo "💡 Run this check in a writable directory"
          exit 1
        fi

        # Files to process
        files="${filesStr}"
        files_processed=0

        for file in $files; do
          if [ -f "$file" ]; then
            printf '%s\n' "🔧 Processing $file..."
            cog -r "$file"
            files_processed=$((files_processed + 1))
          else
            printf '%s\n' "🔧 File not found: $file"
          fi
        done

        if [ $files_processed -eq 0 ]; then
          echo "❌ No files were processed successfully"
          exit 1
        else
          echo "✅ Processed $files_processed file(s) successfully"
        fi
      '';
    };

  # Function to create fawltydeps check with specific Python environment
  makeFawltydepsCheck = { pythonEnv, ignoreUndeclared ? [ ], ignoreUnused ? [ ] }:
    let
      # Automatically ignore fawltydeps itself since it's never imported by analyzed code
      allIgnoredUndeclared = ignoreUndeclared ++ [ "fawltydeps" ];
      allIgnoredUnused = ignoreUnused ++ [ "fawltydeps" ];

      ignoreUndeclaredFlags =
        if allIgnoredUndeclared != [ ]
        then builtins.concatStringsSep " " (map (dep: "--ignore-undeclared ${dep}") allIgnoredUndeclared)
        else "";

      ignoreUnusedFlags =
        if allIgnoredUnused != [ ]
        then builtins.concatStringsSep " " (map (dep: "--ignore-unused ${dep}") allIgnoredUnused)
        else "";

      allFlags = builtins.filter (flag: flag != "") [ ignoreUndeclaredFlags ignoreUnusedFlags ];
      ignoreFlags = builtins.concatStringsSep " " allFlags;

      baseCommand = "fawltydeps${if ignoreFlags != "" then " " + ignoreFlags else ""}";
      verboseCmd = "fawltydeps${if ignoreFlags != "" then " " + ignoreFlags else ""} -v";
    in
    makeCheck {
      name = "fawltydeps";
      description = "Python dependency analysis with FawltyDeps";
      dependencies = [ pythonEnv ];
      command = baseCommand;
      verboseCommand = verboseCmd;
    };

in
{
  inherit makeCheck generateAnalysisScript createAnalysisPackage makeFawltydepsCheck makeGenerateConstantsCheck;
  inherit deadnixCheck nixpkgsFmtCheck statixCheck ruffCheckCheck ruffFormatCheck pyrightCheck trimWhitespaceCheck rustClippyCheck;
}
