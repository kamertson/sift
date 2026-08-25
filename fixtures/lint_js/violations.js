/** Fixture with one clean function and one with an obvious lint violation. */

export function cleanAdd(a, b) {
  return a + b;
}

export function dirtyUnused(x) {
  const unused = 42;
  return x;
}
