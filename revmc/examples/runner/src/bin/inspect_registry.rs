//! One-off: report per-member table size stats (median, total bytes) from a
//! saved skeleton registry, plus a sanity check that every table's byte
//! length is exactly num_variant * 32 (i.e. only PUSH-variant words, nothing
//! else leaked in, such as metadata bytes).
use std::fs;

#[derive(serde::Serialize, serde::Deserialize)]
pub struct RegistryEntry {
    pub skel_hash: u64,
    pub member_hashes: Vec<[u8; 32]>,
    pub variance_pushes: Vec<i32>,
    pub num_variant: u32,
    pub member_data_tables: Vec<Vec<u8>>,
    pub static_jump_checked: bool,
    pub skeleton_mode: String,
    pub classify_mode: String,
}

fn main() {
    let path = std::env::args().nth(1).expect("usage: inspect_registry <path>");
    let data = fs::read(&path).expect("read registry file");
    let entries: Vec<RegistryEntry> =
        bincode::deserialize(&data).expect("deserialize registry");

    let mut sizes: Vec<usize> = Vec::new();
    let mut total_bytes: usize = 0;
    let mut mismatches: Vec<(u64, usize, u32, usize)> = Vec::new();
    for e in &entries {
        let expected = e.num_variant as usize * 32;
        for t in &e.member_data_tables {
            sizes.push(t.len());
            total_bytes += t.len();
            if t.len() != expected {
                mismatches.push((e.skel_hash, t.len(), e.num_variant, expected));
            }
        }
    }
    sizes.sort_unstable();
    let n = sizes.len();
    let median = if n == 0 {
        0
    } else if n % 2 == 1 {
        sizes[n / 2]
    } else {
        (sizes[n / 2 - 1] + sizes[n / 2]) / 2
    };

    println!("file: {path}");
    println!("families (entries): {}", entries.len());
    println!("members (data tables): {n}");
    println!("total bytes (payload only, no framing): {total_bytes}");
    println!("median per-member table bytes: {median}");
    println!("min: {:?}  max: {:?}", sizes.first(), sizes.last());
    println!("file size on disk: {}", data.len());
    println!(
        "skeleton_mode of first entry: {:?}, classify_mode: {:?}",
        entries.first().map(|e| &e.skeleton_mode),
        entries.first().map(|e| &e.classify_mode)
    );
    println!(
        "tables NOT equal to num_variant*32: {} / {}",
        mismatches.len(),
        n
    );
    for (h, got, nv, exp) in mismatches.iter().take(5) {
        println!("  mismatch skel={h:016x} got={got}B num_variant={nv} expected={exp}B");
    }

    // family-size distribution, to separately check whether more/larger
    // families (not per-table content) explain a total-size change.
    let mut fam_sizes: Vec<usize> = entries.iter().map(|e| e.member_hashes.len()).collect();
    fam_sizes.sort_unstable();
    let total_members: usize = fam_sizes.iter().sum();
    println!(
        "family sizes: n_families={} total_members={} min={:?} max={:?} median={:?}",
        fam_sizes.len(),
        total_members,
        fam_sizes.first(),
        fam_sizes.last(),
        fam_sizes.get(fam_sizes.len() / 2)
    );
}
