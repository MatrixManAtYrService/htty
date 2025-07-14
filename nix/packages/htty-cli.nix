# CLI package - provides 'htty' command without altering Python environment
{ pkgs, perSystem, flake, ... }:

let
  # Get the complete htty environment
  httyEnv = perSystem.self.htty;

  # Get project metadata for version from centralized source
  lib = flake.lib pkgs;
  inherit (lib.version) version;
in

pkgs.stdenv.mkDerivation {
  pname = "htty-cli";
  inherit version;

  # Dummy source since we're just creating a wrapper
  src = pkgs.writeText "dummy-source" "";

  dontUnpack = true;
  dontBuild = true;

  installPhase = ''
    runHook preInstall

    # Create bin directory
    mkdir -p $out/bin

    # Create htty CLI wrapper that doesn't expose Python modules
    cat > $out/bin/htty << EOF
    #!/usr/bin/env bash
    # htty CLI - synchronous batch mode for scripting
    # Clear PYTHONPATH to prevent Python environment pollution
    unset PYTHONPATH
    exec ${httyEnv}/bin/python -m htty "\$@"
    EOF
    chmod +x $out/bin/htty

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Headless Terminal - CLI tool (htty only)";
    homepage = "https://github.com/MatrixManAtYrService/ht";
    license = licenses.mit;
    platforms = platforms.unix;
    mainProgram = "htty";
  };
}
