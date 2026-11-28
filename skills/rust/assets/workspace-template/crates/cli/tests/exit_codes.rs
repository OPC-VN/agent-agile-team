use std::process::Command;

fn run(args: &[&str]) -> (Option<i32>, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_cli"))
        .args(args)
        .output()
        .expect("chạy được binary vừa biên dịch");
    (
        out.status.code(),
        String::from_utf8_lossy(&out.stdout).into_owned(),
    )
}

#[test]
fn exit_codes_and_kind() {
    assert_eq!(run(&["echo", "hi"]).0, Some(0));
    let (code, stdout) = run(&["fail"]);
    assert_eq!(code, Some(1));
    assert!(stdout.contains(r#""kind":"failed""#));
    let (code, stdout) = run(&[]);
    assert_eq!(code, Some(2));
    assert!(stdout.contains(r#""kind":"usage""#));
}

/// An argument that is not valid Unicode must give `usage` (exit 2), not a panic (exit 101).
#[cfg(windows)]
#[test]
fn non_unicode_argument_is_usage_not_panic() {
    use std::ffi::OsString;
    use std::os::windows::ffi::OsStringExt;
    let bad = OsString::from_wide(&[0xD800]); // unpaired surrogate
    let out = Command::new(env!("CARGO_BIN_EXE_cli"))
        .arg(&bad)
        .output()
        .expect("chạy được binary vừa biên dịch");
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stdout).contains(r#""kind":"usage""#));
}
