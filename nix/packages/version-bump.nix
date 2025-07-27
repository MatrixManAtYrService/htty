# Version bumping script for htty project
{ pkgs, flake, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib) version;

  # Script to bump version and regenerate files using Cog
  versionBumpScript = pkgs.writeShellScript "version-bump" ''
    set -euo pipefail

    # Parse command line arguments
    BUMP_TYPE=""
    VERBOSE=false

    while [[ $# -gt 0 ]]; do
      case $1 in
        --patch)
          BUMP_TYPE="patch"
          shift
          ;;
        --minor)
          BUMP_TYPE="minor"
          shift
          ;;
        --major)
          BUMP_TYPE="major"
          shift
          ;;
        --prerelease)
          BUMP_TYPE="prerelease"
          shift
          ;;
        -v|--verbose)
          VERBOSE=true
          shift
          ;;
        -h|--help)
          echo "Usage: version-bump [--patch|--minor|--major|--prerelease] [-v|--verbose] [-h|--help]"
          echo ""
          echo "Bump version in nix/lib/version.nix and regenerate all dependent files using Cog."
          echo ""
          echo "Options:"
          echo "  --patch       Increment patch version (e.g., 0.3.0 -> 0.3.1)"
          echo "  --minor       Increment minor version (e.g., 0.3.0 -> 0.4.0)"
          echo "  --major       Increment major version (e.g., 0.3.0 -> 1.0.0)"
          echo "  --prerelease  Add prerelease timestamp (e.g., 0.3.0 -> 0.3.0-2025-July-13-17-24)"
          echo "  -v, --verbose Enable verbose output"
          echo "  -h, --help    Show this help message"
          echo ""
          echo "Prerelease format: YYYY-Month-DD-HH-MM (UTC time)"
          echo "This is useful for CI iterations without bumping the actual version."
          echo ""
          echo "After updating version.nix, runs 'nix run .#codegen' to"
          echo "propagate changes via Cog to all files with version templates."
          exit 0
          ;;
        *)
          echo "Error: Unknown option $1"
          echo "Use --help for usage information"
          exit 1
          ;;
      esac
    done

    if [[ -z "$BUMP_TYPE" ]]; then
      echo "Error: Must specify --patch, --minor, --major, or --prerelease"
      echo "Use --help for usage information"
      exit 1
    fi

    # Check for uncommitted changes
    if ! ${pkgs.git}/bin/git diff-index --quiet HEAD --; then
      echo "Error: Uncommitted changes detected in working directory"
      echo ""
      echo "Please commit or stash your changes before bumping the version:"
      echo "  git add . && git commit -m \"Your changes\""
      echo "  # OR"
      echo "  git stash"
      echo ""
      echo "This prevents version bump conflicts with uncommitted work."
      exit 1
    fi

    # Get current version components from Nix
    CURRENT_MAJOR=${builtins.toString version.major}
    CURRENT_MINOR=${builtins.toString version.minor}
    CURRENT_PATCH=${builtins.toString version.patch}
    CURRENT_VERSION="$CURRENT_MAJOR.$CURRENT_MINOR.$CURRENT_PATCH"

    if [[ "$VERBOSE" == "true" ]]; then
      echo "Current version: $CURRENT_VERSION"
      echo "Bump type: $BUMP_TYPE"
    fi

    # Calculate new version components and set environment variables for Cog
    case $BUMP_TYPE in
      patch)
        export HTTY_VERSION_MAJOR=$CURRENT_MAJOR
        export HTTY_VERSION_MINOR=$CURRENT_MINOR
        export HTTY_VERSION_PATCH=$((CURRENT_PATCH + 1))
        export HTTY_VERSION_PRERELEASE=""
        NEW_VERSION="$HTTY_VERSION_MAJOR.$HTTY_VERSION_MINOR.$HTTY_VERSION_PATCH"
        ;;
      minor)
        export HTTY_VERSION_MAJOR=$CURRENT_MAJOR
        export HTTY_VERSION_MINOR=$((CURRENT_MINOR + 1))
        export HTTY_VERSION_PATCH=0
        export HTTY_VERSION_PRERELEASE=""
        NEW_VERSION="$HTTY_VERSION_MAJOR.$HTTY_VERSION_MINOR.$HTTY_VERSION_PATCH"
        ;;
      major)
        export HTTY_VERSION_MAJOR=$((CURRENT_MAJOR + 1))
        export HTTY_VERSION_MINOR=0
        export HTTY_VERSION_PATCH=0
        export HTTY_VERSION_PRERELEASE=""
        NEW_VERSION="$HTTY_VERSION_MAJOR.$HTTY_VERSION_MINOR.$HTTY_VERSION_PATCH"
        ;;
      prerelease)
        # Generate UTC timestamp in Python-compatible format: dev202507131724
        UTC_TIMESTAMP=$(${pkgs.coreutils}/bin/date -u '+dev%Y%m%d%H%M')
        export HTTY_VERSION_MAJOR=$CURRENT_MAJOR
        export HTTY_VERSION_MINOR=$CURRENT_MINOR
        export HTTY_VERSION_PATCH=$CURRENT_PATCH
        export HTTY_VERSION_PRERELEASE="$UTC_TIMESTAMP"
        NEW_VERSION="$CURRENT_MAJOR.$CURRENT_MINOR.$CURRENT_PATCH-$UTC_TIMESTAMP"

        if [[ "$VERBOSE" == "true" ]]; then
          echo "Generated prerelease timestamp: $UTC_TIMESTAMP"
        fi
        ;;
    esac

    # Update version.nix using Cog
    [[ "$VERBOSE" == "true" ]] && set -x
    ${pkgs.python3Packages.cogapp}/bin/cog -r nix/lib/version.nix
    [[ "$VERBOSE" == "true" ]] && set +x

    echo "Bumping version: $CURRENT_VERSION -> $NEW_VERSION"

    # Run codegen to propagate the version changes via Cog
    [[ "$VERBOSE" == "true" ]] && set -x
    if [[ "$VERBOSE" == "true" ]]; then
      ${pkgs.nix}/bin/nix run .#codegen -- -v
    else
      ${pkgs.nix}/bin/nix run .#codegen
    fi

    # Update Cargo.lock by updating dependency info without building
    ${pkgs.cargo}/bin/cargo update --manifest-path htty-core/Cargo.toml --package htty_core
    [[ "$VERBOSE" == "true" ]] && set +x

    # Update uv.lock files by running lock command (doesn't require building)
    [[ "$VERBOSE" == "true" ]] && set -x

    (cd htty-core && ${pkgs.uv}/bin/uv lock)

    # Set up Cog environment variables from shared source
    ${pkgs.lib.concatStringsSep "\n" (pkgs.lib.mapAttrsToList (k: v: "export ${k}=${pkgs.lib.escapeShellArg (toString v)}") lib.cogEnv)}

    # For htty, use local dependency for uv lock to avoid PyPI dependency resolution
    export HTTY_USE_LOCAL_CORE=true
    export HTTY_VERSION="$NEW_VERSION"
    ${pkgs.python3Packages.cogapp}/bin/cog -r htty/pyproject.toml

    (cd htty && ${pkgs.uv}/bin/uv lock)

    # Restore PyPI dependency for final pyproject.toml
    unset HTTY_USE_LOCAL_CORE
    ${pkgs.python3Packages.cogapp}/bin/cog -r htty/pyproject.toml

    [[ "$VERBOSE" == "true" ]] && set +x

    echo "✅ Version bump complete: $CURRENT_VERSION -> $NEW_VERSION"
    echo "💡 All files with version templates have been updated via Cog"
    echo ""
    if [[ "$BUMP_TYPE" == "prerelease" ]]; then
      echo "🧪 Prerelease version created for CI testing"
      echo "💡 Use --patch/--minor/--major for final release"
    else
      echo "🚀 Ready to commit and release version $NEW_VERSION"
      echo ""
      echo "💡 Suggestion:"
      echo "git add . ; git commit -m \"Version: $NEW_VERSION\" ; git tag v$NEW_VERSION ; git push --tags github main"
    fi
  '';

in
pkgs.stdenv.mkDerivation {
  pname = "version-bump";
  inherit (version) version;

  dontUnpack = true;
  dontBuild = true;

  installPhase = ''
    mkdir -p $out/bin
    cp ${versionBumpScript} $out/bin/version-bump
    chmod +x $out/bin/version-bump
  '';

  meta = with pkgs.lib; {
    description = "Version bumping script for htty project with prerelease support";
    mainProgram = "version-bump";
    platforms = platforms.unix;
  };
}
