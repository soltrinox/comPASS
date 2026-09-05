//! comPASS Route+Graph read core (WASM-safe).
//!
//! Pure decide-from-snapshot: classify + score + fail-open defaults.
//! No filesystem, no env keys, no fetch. Host supplies snapshot bytes + clock.

use serde_json::{json, Value};
use std::cmp::Ordering;

pub const CORE_MODULE_VERSION: &str = "0.1.0";
pub const ABI_MIN: &str = "1.0.0";
pub const ABI_MAX: &str = "1.999.0";

pub const DEFAULT_MODEL_VERSION_ID: &str = "default";
pub const DEFAULT_QUALITY: f64 = 0.5;
pub const DEFAULT_COST: f64 = 1.0;
pub const DEFAULT_LAMBDA: f64 = 1.0;
pub const DEFAULT_TASK_CLASS: &str = "general";

#[derive(Clone, Debug)]
pub struct RouteConfig {
    pub default_model_version_id: String,
    pub lambda_cost: f64,
    pub default_quality: f64,
    pub default_cost: f64,
}

impl Default for RouteConfig {
    fn default() -> Self {
        Self {
            default_model_version_id: DEFAULT_MODEL_VERSION_ID.to_string(),
            lambda_cost: DEFAULT_LAMBDA,
            default_quality: DEFAULT_QUALITY,
            default_cost: DEFAULT_COST,
        }
    }
}

fn bandit_score(quality: f64, cost: f64, lambda_cost: f64) -> f64 {
    quality - lambda_cost * cost
}

fn fail_open(
    cfg: &RouteConfig,
    reason_code: &str,
    task_class_id: &str,
    decided_at: &str,
    constraints: Vec<String>,
) -> Value {
    let rationale = format!("fail-open: {reason_code}");
    let s = bandit_score(cfg.default_quality, cfg.default_cost, cfg.lambda_cost);
    json!({
        "selected_model_version_id": cfg.default_model_version_id,
        "task_class_id": task_class_id,
        "score": s,
        "lambda": cfg.lambda_cost,
        "scores": { cfg.default_model_version_id.clone(): s },
        "rationale": rationale,
        "fail_open": true,
        "default_reason": reason_code,
        "decided_at": decided_at,
        "constraints_applied": constraints,
        "abi_min": ABI_MIN,
        "abi_max": ABI_MAX,
        "module_version": CORE_MODULE_VERSION,
    })
}

fn tokenize(text: &str, limit: usize) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut cur = String::new();
    for ch in text.chars() {
        let ok = ch.is_ascii_alphanumeric() || matches!(ch, '_' | '.' | '/' | '#' | '-');
        if ok {
            if cur.is_empty() {
                if ch.is_ascii_alphanumeric() {
                    cur.push(ch.to_ascii_lowercase());
                }
            } else {
                cur.push(ch.to_ascii_lowercase());
            }
        } else if !cur.is_empty() {
            if cur.len() >= 2 {
                tokens.push(cur.clone());
            }
            cur.clear();
            if tokens.len() >= limit * 4 {
                break;
            }
        }
    }
    if cur.len() >= 2 {
        tokens.push(cur);
    }
    tokens.sort_by(|a, b| b.len().cmp(&a.len()).then(a.cmp(b)));
    tokens.dedup();
    tokens.into_iter().take(limit).collect()
}

fn keyword_match(token: &str, seed: &str) -> bool {
    token.starts_with(seed) || token.contains(seed)
}

pub fn classify(request: &str) -> String {
    let kws = tokenize(request, 64);
    if kws.is_empty() {
        return DEFAULT_TASK_CLASS.to_string();
    }
    let clusters: &[(&str, &[&str])] = &[
        (
            "code_generation",
            &[
                "code", "implement", "function", "class", "refactor", "bug", "fix", "compile",
                "test",
            ],
        ),
        (
            "multi_step_plan",
            &["plan", "roadmap", "milestone", "orchestrat", "multi-step", "architecture"],
        ),
        (
            "structured_output",
            &["json", "schema", "yaml", "structured", "table", "csv"],
        ),
        (
            "long_context",
            &["summarize", "transcript", "long", "document", "corpus", "context"],
        ),
        (
            "agentic_tool_use",
            &["tool", "browser", "shell", "api", "call", "agent"],
        ),
    ];
    let order = [
        "general",
        "structured_output",
        "long_context",
        "code_generation",
        "agentic_tool_use",
        "multi_step_plan",
    ];
    let mut best_class = DEFAULT_TASK_CLASS.to_string();
    let mut best_score = 0i32;
    for task_class in order {
        let seeds = clusters
            .iter()
            .find(|(n, _)| *n == task_class)
            .map(|(_, s)| *s)
            .unwrap_or(&[]);
        let score = kws
            .iter()
            .filter(|k| seeds.iter().any(|s| keyword_match(k, s)))
            .count() as i32;
        if score >= best_score {
            best_score = score;
            best_class = if score > 0 {
                task_class.to_string()
            } else {
                DEFAULT_TASK_CLASS.to_string()
            };
        }
    }
    if best_score > 0 {
        best_class
    } else {
        DEFAULT_TASK_CLASS.to_string()
    }
}

fn parse_snapshot(raw: Option<&str>) -> Result<(String, Vec<Value>), &'static str> {
    let Some(text) = raw else {
        return Err("snapshot_missing");
    };
    if text.trim().is_empty() {
        return Err("snapshot_missing");
    }
    let data: Value = match serde_json::from_str(text) {
        Ok(v) => v,
        Err(_) => return Err("snapshot_corrupt"),
    };
    let obj = match data.as_object() {
        Some(o) => o,
        None => return Err("snapshot_corrupt"),
    };
    let nodes = match obj.get("nodes") {
        Some(Value::Array(a)) => a.clone(),
        Some(_) => return Err("snapshot_corrupt"),
        None => Vec::new(),
    };
    let edges_ok = match obj.get("edges") {
        None => true,
        Some(Value::Array(_)) => true,
        Some(_) => false,
    };
    if !edges_ok {
        return Err("snapshot_corrupt");
    }
    let schema = obj
        .get("schema")
        .and_then(|v| v.as_str())
        .unwrap_or("model-graph/v1")
        .to_string();
    Ok((schema, nodes))
}

fn candidates_from_nodes(
    nodes: &[Value],
    default_quality: f64,
    default_cost: f64,
) -> Vec<(String, f64, f64)> {
    let mut out = Vec::new();
    for n in nodes {
        let Some(obj) = n.as_object() else {
            continue;
        };
        if obj.get("kind").and_then(|v| v.as_str()) != Some("ModelVersion") {
            continue;
        }
        let status = obj
            .get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("active");
        if status != "active" {
            continue;
        }
        let Some(id) = obj.get("id").and_then(|v| v.as_str()) else {
            continue;
        };
        if id.is_empty() {
            continue;
        }
        let attrs = obj.get("attrs").and_then(|v| v.as_object());
        let quality = attrs
            .and_then(|a| a.get("quality").or_else(|| a.get("expected_quality")))
            .and_then(|v| v.as_f64())
            .unwrap_or(default_quality);
        let cost = attrs
            .and_then(|a| a.get("cost").or_else(|| a.get("expected_cost")))
            .and_then(|v| v.as_f64())
            .unwrap_or(default_cost);
        out.push((id.to_string(), quality, cost));
    }
    out
}

/// Decide from host-fed snapshot JSON text. Mirrors Python `compass.core.decide_from_snapshot`.
pub fn decide_from_snapshot_json(
    request: &str,
    snapshot_json: Option<&str>,
    cfg: &RouteConfig,
    now_iso: &str,
) -> Value {
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        decide_inner(request, snapshot_json, cfg, now_iso)
    }));
    match result {
        Ok(v) => v,
        Err(_) => fail_open(
            cfg,
            "module_trap",
            DEFAULT_TASK_CLASS,
            now_iso,
            vec!["exception:panic".to_string()],
        ),
    }
}

fn decide_inner(
    request: &str,
    snapshot_json: Option<&str>,
    cfg: &RouteConfig,
    now_iso: &str,
) -> Value {
    let (_schema, nodes) = match parse_snapshot(snapshot_json) {
        Ok(v) => v,
        Err(code) => {
            return fail_open(cfg, code, DEFAULT_TASK_CLASS, now_iso, vec![]);
        }
    };
    let task_class = classify(request);
    let cands = candidates_from_nodes(&nodes, cfg.default_quality, cfg.default_cost);
    if cands.is_empty() {
        return fail_open(cfg, "no_candidates", &task_class, now_iso, vec![]);
    }
    let scores: Vec<(String, f64, f64)> = cands
        .into_iter()
        .map(|(id, q, c)| (id, bandit_score(q, c, cfg.lambda_cost), c))
        .collect();
    if scores.is_empty() {
        return fail_open(cfg, "no_candidates", &task_class, now_iso, vec![]);
    }
    let best_score = scores
        .iter()
        .map(|(_, s, _)| *s)
        .fold(f64::NEG_INFINITY, f64::max);
    let mut tied: Vec<&(String, f64, f64)> = scores
        .iter()
        .filter(|(_, s, _)| (*s - best_score).abs() < 1e-12)
        .collect();
    let mut constraints: Vec<String> = Vec::new();
    if tied.len() > 1 {
        tied.sort_by(|a, b| {
            a.2.partial_cmp(&b.2)
                .unwrap_or(Ordering::Equal)
                .then_with(|| a.0.cmp(&b.0))
        });
        constraints.push("tie_break:lower_cost".to_string());
    }
    let best = tied[0];
    let mut score_map = serde_json::Map::new();
    for (id, s, _) in &scores {
        score_map.insert(id.clone(), json!(s));
    }
    json!({
        "selected_model_version_id": best.0,
        "task_class_id": task_class,
        "score": best.1,
        "lambda": cfg.lambda_cost,
        "scores": score_map,
        "rationale": "highest score under quality−λ·cost",
        "fail_open": false,
        "default_reason": Value::Null,
        "decided_at": now_iso,
        "constraints_applied": constraints,
        "abi_min": ABI_MIN,
        "abi_max": ABI_MAX,
        "module_version": CORE_MODULE_VERSION,
    })
}

static mut LAST_OUT: Vec<u8> = Vec::new();

#[no_mangle]
pub extern "C" fn compass_alloc(size: u32) -> *mut u8 {
    let mut buf = vec![0u8; size as usize];
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

#[no_mangle]
pub extern "C" fn compass_free(ptr: *mut u8, size: u32) {
    if ptr.is_null() || size == 0 {
        return;
    }
    unsafe {
        let _ = Vec::from_raw_parts(ptr, size as usize, size as usize);
    }
}

#[no_mangle]
pub extern "C" fn compass_decide_json(
    request_ptr: *const u8,
    request_len: u32,
    snapshot_ptr: *const u8,
    snapshot_len: u32,
    now_ptr: *const u8,
    now_len: u32,
) -> *const u8 {
    let request = unsafe {
        if request_ptr.is_null() || request_len == 0 {
            ""
        } else {
            std::str::from_utf8(std::slice::from_raw_parts(
                request_ptr,
                request_len as usize,
            ))
            .unwrap_or("")
        }
    };
    let snapshot = unsafe {
        if snapshot_ptr.is_null() || snapshot_len == 0 {
            None
        } else {
            std::str::from_utf8(std::slice::from_raw_parts(
                snapshot_ptr,
                snapshot_len as usize,
            ))
            .ok()
        }
    };
    let now = unsafe {
        if now_ptr.is_null() || now_len == 0 {
            ""
        } else {
            std::str::from_utf8(std::slice::from_raw_parts(now_ptr, now_len as usize))
                .unwrap_or("")
        }
    };
    let cfg = RouteConfig::default();
    let decision = decide_from_snapshot_json(request, snapshot, &cfg, now);
    let bytes = serde_json::to_vec(&decision).unwrap_or_else(|_| {
        b"{\"fail_open\":true,\"default_reason\":\"module_trap\"}".to_vec()
    });
    unsafe {
        LAST_OUT = bytes;
        LAST_OUT.as_ptr()
    }
}

#[no_mangle]
pub extern "C" fn compass_last_len() -> u32 {
    unsafe { LAST_OUT.len() as u32 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fixture_picks_cheap() {
        let snap = r#"{
  "schema": "model-graph/v1",
  "nodes": [
    {"id":"urn:mg:model:cheap","kind":"ModelVersion","status":"active","attrs":{"quality":0.7,"cost":0.1}},
    {"id":"urn:mg:model:pricey","kind":"ModelVersion","status":"active","attrs":{"quality":0.75,"cost":0.5}}
  ],
  "edges": []
}"#;
        let v = decide_from_snapshot_json(
            "implement a function",
            Some(snap),
            &RouteConfig::default(),
            "2026-09-05T00:00:00Z",
        );
        assert_eq!(v["selected_model_version_id"], "urn:mg:model:cheap");
        assert_eq!(v["task_class_id"], "code_generation");
        assert_eq!(v["fail_open"], false);
    }

    #[test]
    fn missing_corrupt_empty() {
        let cfg = RouteConfig::default();
        assert_eq!(
            decide_from_snapshot_json("x", None, &cfg, "")["default_reason"],
            "snapshot_missing"
        );
        assert_eq!(
            decide_from_snapshot_json("x", Some("{bad"), &cfg, "")["default_reason"],
            "snapshot_corrupt"
        );
        assert_eq!(
            decide_from_snapshot_json(
                "x",
                Some(r#"{"schema":"model-graph/v1","nodes":[],"edges":[]}"#),
                &cfg,
                ""
            )["default_reason"],
            "no_candidates"
        );
    }
}
