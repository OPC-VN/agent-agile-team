#![forbid(unsafe_code)]

use std::process::ExitCode;

fn main() -> ExitCode {
    // args_os: std::env::args() panics on a non-UTF-8 argument; map it to `usage` (exit 2) instead.
    let args: Option<Vec<String>> = std::env::args_os()
        .skip(1)
        .map(|a| a.into_string().ok())
        .collect();
    let outcome = match args {
        Some(args) => cli::run(&args),
        None => cli::usage(),
    };
    println!("{}", outcome.line);
    ExitCode::from(outcome.code)
}
