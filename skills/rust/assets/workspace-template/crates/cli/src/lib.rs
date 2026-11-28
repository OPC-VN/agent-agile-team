//! Logic lõi của CLI mẫu, tách khỏi `main` để test được.
#![forbid(unsafe_code)]

/// Kết quả một lần chạy: mã thoát và dòng JSON in ra stdout.
#[derive(Debug, PartialEq, Eq)]
pub struct Outcome {
    pub code: u8,
    pub line: String,
}

/// Chạy lệnh từ danh sách đối số (không gồm tên chương trình).
///
/// - `echo <chữ>`: exit 0, kind `ok`.
/// - `fail`: exit 1, kind `failed`.
/// - mọi trường hợp khác: exit 2, kind `usage`.
pub fn run(args: &[String]) -> Outcome {
    match args {
        [cmd, text] if cmd == "echo" => Outcome {
            code: 0,
            line: format!(r#"{{"kind":"ok","text":"{}"}}"#, escape(text)),
        },
        [cmd] if cmd == "fail" => Outcome {
            code: 1,
            line: r#"{"kind":"failed"}"#.to_string(),
        },
        _ => usage(),
    }
}

/// Kết quả `usage` (exit 2): đối số sai, hoặc đối số không đổi được sang UTF-8 (xem `main`).
pub fn usage() -> Outcome {
    Outcome {
        code: 2,
        line: r#"{"kind":"usage"}"#.to_string(),
    }
}

fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", u32::from(c))),
            c => out.push(c),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| (*s).to_string()).collect()
    }

    #[test]
    fn echo_ok() {
        let o = run(&args(&["echo", "xin chào"]));
        assert_eq!(o.code, 0);
        assert_eq!(o.line, r#"{"kind":"ok","text":"xin chào"}"#);
    }

    #[test]
    fn echo_escapes_quotes() {
        let o = run(&args(&["echo", "a\"b"]));
        assert_eq!(o.line, r#"{"kind":"ok","text":"a\"b"}"#);
    }

    #[test]
    fn fail_exit_1() {
        assert_eq!(run(&args(&["fail"])).code, 1);
    }

    #[test]
    fn usage_exit_2() {
        let o = run(&args(&[]));
        assert_eq!(o.code, 2);
        assert_eq!(o.line, r#"{"kind":"usage"}"#);
        assert_eq!(run(&args(&["echo"])).code, 2);
    }

    #[test]
    fn test_code_may_unwrap_and_panic() {
        let n: u8 = "7".parse().unwrap();
        if n != 7 {
            panic!("không thể xảy ra");
        }
    }
}
