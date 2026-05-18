//! super_solver: native maze solver for the maze_api ASCII format.
//!
//! Strategy:
//!   1. Parse the ASCII payload exactly once into a packed passages grid
//!      (4 bits per cell = N/S/E/W openings). No HashMaps, no dataclasses,
//!      no per-cell allocations.
//!   2. Identify the start (P or S) and the unique boundary exit during the
//!      same pass.
//!   3. Run BFS on cell linear indices (r*N + c). The frontier lives in a
//!      single Vec<u32> used as a flat ring (head pointer + push).
//!   4. Reconstruct the path from a contiguous parent_dir: Vec<u8>.
//!
//! ABI:
//!   extern "C" fn solve(ascii_ptr, ascii_len, out_ptr, out_cap) -> i32
//!     Writes the move string (ASCII: 'N','S','E','W') into `out_ptr`,
//!     returns the number of bytes written, or a negative error code:
//!         -1 invalid ASCII shape
//!         -2 no start marker
//!         -3 no boundary exit
//!         -4 unreachable goal
//!         -5 output buffer too small

#![allow(clippy::missing_safety_doc)]

const N_BIT: u8 = 1 << 0;
const S_BIT: u8 = 1 << 1;
const E_BIT: u8 = 1 << 2;
const W_BIT: u8 = 1 << 3;

const DIR_UNVISITED: u8 = 0;
const DIR_N: u8 = b'N';
const DIR_S: u8 = b'S';
const DIR_E: u8 = b'E';
const DIR_W: u8 = b'W';
const DIR_ROOT: u8 = 1; // sentinel marking the start cell (not a real move)

#[derive(Debug)]
struct Parsed {
    n: usize,
    passages: Vec<u8>,
    start: u32,
    exit_cell: u32,
    exit_dir: u8,
}

#[inline]
fn line_width(ascii: &[u8]) -> Option<usize> {
    // Lines are terminated with '\n'; we keep the '\n' in the width
    // so cell index arithmetic is uniform.
    ascii.iter().position(|&b| b == b'\n').map(|i| i + 1)
}

fn parse(ascii: &[u8]) -> Result<Parsed, i32> {
    let lw = line_width(ascii).ok_or(-1)?;
    // Inner content width = lw - 1 (drop the '\n'). Format: 4*N + 1 chars.
    if lw < 2 {
        return Err(-1);
    }
    let inner = lw - 1;
    if (inner - 1) % 4 != 0 {
        return Err(-1);
    }
    let n = (inner - 1) / 4;
    // Account for the (commonly missing) trailing newline on the last line.
    let total_lines = (ascii.len() + 1) / lw;
    if total_lines < 2 * n + 1 {
        return Err(-1);
    }

    let mut passages = vec![0u8; n * n];
    let mut start: i64 = -1;
    let mut start_marker: u8 = 0; // 'P' beats 'S' (player position)
    let exit_cell: i64;
    let exit_dir: u8;
    let mut goal_marker_cell: i64 = -1;
    let mut boundary_openings: Vec<(u32, u8)> = Vec::with_capacity(4);

    // Cell (r, c):
    //   center byte:    ((2r+1) * lw) + (4c + 2)
    //   N wall sample:  ((2r)   * lw) + (4c + 2)
    //   S wall sample:  ((2r+2) * lw) + (4c + 2)
    //   W wall byte:    ((2r+1) * lw) + (4c)
    //   E wall byte:    ((2r+1) * lw) + (4c + 4)
    //
    // Horizontal walls span 3 chars; we just sample the middle (4c+2):
    // a passage shows ' ' there, a wall shows '-'.
    for r in 0..n {
        let interior_off = (2 * r + 1) * lw;
        let north_off = (2 * r) * lw;
        let south_off = (2 * r + 2) * lw;
        for c in 0..n {
            let cell_idx = r * n + c;
            let cx = 4 * c + 2;
            let center = ascii[interior_off + cx];
            match center {
                b'P' => {
                    start = cell_idx as i64;
                    start_marker = b'P';
                }
                b'S' => {
                    if start_marker != b'P' {
                        start = cell_idx as i64;
                        start_marker = b'S';
                    }
                }
                b'X' => {
                    goal_marker_cell = cell_idx as i64;
                }
                _ => {}
            }

            let n_open = ascii[north_off + cx] == b' ';
            let s_open = ascii[south_off + cx] == b' ';
            let w_open = ascii[interior_off + 4 * c] == b' ';
            let e_open = ascii[interior_off + 4 * c + 4] == b' ';

            let mut p = 0u8;
            if n_open {
                if r == 0 {
                    boundary_openings.push((cell_idx as u32, DIR_N));
                } else {
                    p |= N_BIT;
                }
            }
            if s_open {
                if r == n - 1 {
                    boundary_openings.push((cell_idx as u32, DIR_S));
                } else {
                    p |= S_BIT;
                }
            }
            if w_open {
                if c == 0 {
                    boundary_openings.push((cell_idx as u32, DIR_W));
                } else {
                    p |= W_BIT;
                }
            }
            if e_open {
                if c == n - 1 {
                    boundary_openings.push((cell_idx as u32, DIR_E));
                } else {
                    p |= E_BIT;
                }
            }
            passages[cell_idx] = p;
        }
    }

    if start < 0 {
        return Err(-2);
    }

    if goal_marker_cell >= 0 {
        let g = goal_marker_cell as u32;
        let mut matched: Option<u8> = None;
        let mut count = 0;
        for (cell, dir) in &boundary_openings {
            if *cell == g {
                count += 1;
                matched = Some(*dir);
            }
        }
        if count > 1 {
            return Err(-3);
        }
        exit_cell = g as i64;
        exit_dir = matched.unwrap_or(0);
    } else {
        if boundary_openings.len() != 1 {
            return Err(-3);
        }
        exit_cell = boundary_openings[0].0 as i64;
        exit_dir = boundary_openings[0].1;
    }

    Ok(Parsed {
        n,
        passages,
        start: start as u32,
        exit_cell: exit_cell as u32,
        exit_dir,
    })
}

fn bfs(parsed: &Parsed) -> Result<Vec<u8>, i32> {
    let n = parsed.n;
    let total = n * n;
    let mut parent_dir = vec![DIR_UNVISITED; total];
    parent_dir[parsed.start as usize] = DIR_ROOT;

    let mut queue: Vec<u32> = Vec::with_capacity(total);
    queue.push(parsed.start);
    let mut head = 0usize;

    let n_u = n as u32;
    let exit = parsed.exit_cell;
    let mut found = false;

    while head < queue.len() {
        let curr = queue[head];
        head += 1;
        if curr == exit {
            found = true;
            break;
        }
        let curr_u = curr as usize;
        let p = parsed.passages[curr_u];

        if p & N_BIT != 0 {
            let nb = curr - n_u;
            let nbi = nb as usize;
            if parent_dir[nbi] == DIR_UNVISITED {
                parent_dir[nbi] = DIR_N;
                queue.push(nb);
            }
        }
        if p & S_BIT != 0 {
            let nb = curr + n_u;
            let nbi = nb as usize;
            if parent_dir[nbi] == DIR_UNVISITED {
                parent_dir[nbi] = DIR_S;
                queue.push(nb);
            }
        }
        if p & E_BIT != 0 {
            let nb = curr + 1;
            let nbi = nb as usize;
            if parent_dir[nbi] == DIR_UNVISITED {
                parent_dir[nbi] = DIR_E;
                queue.push(nb);
            }
        }
        if p & W_BIT != 0 {
            let nb = curr - 1;
            let nbi = nb as usize;
            if parent_dir[nbi] == DIR_UNVISITED {
                parent_dir[nbi] = DIR_W;
                queue.push(nb);
            }
        }
    }

    if !found {
        return Err(-4);
    }

    // Reconstruct moves walking backwards from exit_cell.
    let mut moves: Vec<u8> = Vec::with_capacity(total);
    let mut curr = parsed.exit_cell;
    while curr != parsed.start {
        let d = parent_dir[curr as usize];
        moves.push(d);
        curr = match d {
            DIR_N => curr + n_u, // we came from south of curr
            DIR_S => curr - n_u,
            DIR_E => curr - 1,
            DIR_W => curr + 1,
            _ => return Err(-4),
        };
    }
    moves.reverse();
    if parsed.exit_dir != 0 {
        moves.push(parsed.exit_dir);
    }
    Ok(moves)
}

/// # Safety
/// `ascii_ptr` must point to `ascii_len` valid bytes. `out_ptr` must point to
/// at least `out_cap` writable bytes.
#[no_mangle]
pub unsafe extern "C" fn solve(
    ascii_ptr: *const u8,
    ascii_len: usize,
    out_ptr: *mut u8,
    out_cap: usize,
) -> i32 {
    if ascii_ptr.is_null() || out_ptr.is_null() {
        return -1;
    }
    let ascii = std::slice::from_raw_parts(ascii_ptr, ascii_len);
    let parsed = match parse(ascii) {
        Ok(p) => p,
        Err(e) => return e,
    };
    let moves = match bfs(&parsed) {
        Ok(m) => m,
        Err(e) => return e,
    };
    if moves.len() > out_cap {
        return -5;
    }
    std::ptr::copy_nonoverlapping(moves.as_ptr(), out_ptr, moves.len());
    moves.len() as i32
}
