.pragma library

function normalize(index, count) {
    if (count <= 0) return 0
    return ((index % count) + count) % count
}

function next(index, direction, count) {
    if (count <= 1) return 0
    return normalize(index + direction, count)
}
