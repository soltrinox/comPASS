//! WASI CLI for desktop / CI Wasmer runs.
//!
//! Usage:
//!   compass-decide --request "implement a function" --snapshot path.json [--now ISO]
//!   compass-decide --request "x" --snapshot-stdin < snapshot.json
//!   compass-decide --fail-open-demo missing|corrupt|empty

use compass_core::{decide_from_snapshot_json, RouteConfig};
use std::env;
use std::io::{self, Read};
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut request = String::from("implement a function");
    let mut snapshot_path: Option<String> = None;
    let mut snapshot_stdin = false;
    let mut now = String::from("2026-09-05T00:00:00Z");
    let mut fail_open_demo: Option<String> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--request" | "-r" => {
                i += 1;
                request = args.get(i).cloned().unwrap_or_default();
            }
            "--snapshot" | "-s" => {
                i += 1;
                snapshot_path = args.get(i).cloned();
            }
            "--snapshot-stdin" => snapshot_stdin = true,
            "--now" => {
                i += 1;
                now = args.get(i).cloned().unwrap_or_default();
            }
            "--fail-open-demo" => {
                i += 1;
                fail_open_demo = args.get(i).cloned();
            }
            "-h" | "--help" => {
                eprintln!(
                    "compass-decide — comPASS Route+Graph WASM core (WASI)\n\
                     --request TEXT\n--snapshot PATH | --snapshot-stdin\n--now ISO\n--fail-open-demo missing|corrupt|empty"
                );
                process::exit(0);
            }
            other => {
                eprintln!("unknown arg: {other}");
                process::exit(2);
            }
        }
        i += 1;
    }

    let cfg = RouteConfig::default();
    let decision = if let Some(demo) = fail_open_demo {
        match demo.as_str() {
            "missing" => decide_from_snapshot_json(&request, None, &cfg, &now),
            "corrupt" => decide_from_snapshot_json(&request, Some("{truncated"), &cfg, &now),
            "empty" => decide_from_snapshot_json(
                &request,
                Some(r#"{"schema":"model-graph/v1","nodes":[],"edges":[]}"#),
                &cfg,
                &now,
            ),
            _ => {
                eprintln!("unknown fail-open-demo: {demo}");
                process::exit(2);
            }
        }
    } else {
        let snap_text = if snapshot_stdin {
            let mut buf = String::new();
            io::stdin().read_to_string(&mut buf).unwrap_or(0);
            Some(buf)
        } else if let Some(path) = snapshot_path {
            match std::fs::read_to_string(&path) {
                Ok(s) => Some(s),
                Err(e) => {
                    eprintln!("read snapshot: {e}");
                    None
                }
            }
        } else {
            eprintln!("need --snapshot PATH or --snapshot-stdin or --fail-open-demo");
            process::exit(2);
        };
        decide_from_snapshot_json(&request, snap_text.as_deref(), &cfg, &now)
    };

    println!("{}", serde_json::to_string(&decision).expect("serialize"));
}
