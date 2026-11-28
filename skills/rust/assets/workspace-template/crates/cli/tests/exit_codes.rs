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
