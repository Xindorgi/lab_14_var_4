extern crate cbindgen;

use std::env;
use std::path::PathBuf;

fn main() {
    let crate_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let output_file = PathBuf::from(&crate_dir)
        .join("include")
        .join("news_validator.h");
    
    // Create include directory if it doesn't exist
    std::fs::create_dir_all(output_file.parent().unwrap()).unwrap();
    
    // Generate C header
    cbindgen::generate(&crate_dir)
        .expect("Unable to generate bindings")
        .write_to_file(&output_file);
    
    println!("cargo:rerun-if-changed=src/lib.rs");
    println!("cargo:rerun-if-changed=build.rs");
    
    // Tell Cargo to link the library
    println!("cargo:rustc-link-lib=static=news_validator");
    println!("cargo:rustc-link-search=native={}", env::var("OUT_DIR").unwrap());
}