mod bench_common;

use std::time::{Duration, Instant};

use criterion::{black_box, criterion_group, criterion_main, Criterion};

const FIXTURE_RELATIVE_PATH: &str = "data/uniswap-t100-c20.json";

pub fn bench_first_uniswap_tx(c: &mut Criterion) {
    let fixture =
        bench_common::Fixture::load(FIXTURE_RELATIVE_PATH).expect("failed to load JSON fixture");

    let mut group = c.benchmark_group("uniswap_first_transaction");
    group.bench_function("plain_execution", |b| {
        b.iter_custom(|iters| {
            let mut total = Duration::ZERO;
            for _ in 0..iters {
                let start = Instant::now();
                let result = fixture.run_plain().expect("plain execution failed");
                total += start.elapsed();
                black_box(result);
            }
            total
        });
    });
    group.bench_function("jit_optimized", |b| {
        b.iter_custom(|iters| {
            let mut total = Duration::ZERO;
            for _ in 0..iters {
                let start = Instant::now();
                let result = fixture.run_jit().expect("jit execution failed");
                total += start.elapsed();
                black_box(result);
            }
            total
        });
    });
    group.finish();
}

criterion_group!(benches, bench_first_uniswap_tx);
criterion_main!(benches);
