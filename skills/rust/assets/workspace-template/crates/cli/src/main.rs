#![forbid(unsafe_code)]

use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let outcome = cli::run(&args);
    println!("{}", outcome.line);
    ExitCode::from(outcome.code)
}
