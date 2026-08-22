/**
 * Frontend boundary rules (Spec 00 plan §1.2 rule 4):
 * features are isolated — no cross-feature imports; features may use packages/* and
 * their own folder. Consumed by apps via `depcruise --config`.
 */
module.exports = {
  forbidden: [
    {
      name: "no-cross-feature-imports",
      severity: "error",
      comment: "Features must not import from sibling features",
      from: { path: "^src/features/([^/]+)/" },
      to: { path: "^src/features/(?!$1)([^/]+)/" },
    },
    {
      name: "no-circular",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: true,
  },
};
