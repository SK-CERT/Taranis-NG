const { spawnSync } = require("child_process");
const path = require("path");

const cwd = path.resolve(__dirname, "..");

function run(cmd, args) {
    // console.log("CMD:", cmd);
    // console.log("ARGS:", args);
    // console.log("CWD:", cwd);

    const result = spawnSync(cmd, args, {
        cwd,
        stdio: "inherit",
        shell: true
    });
    // console.log("STATUS:", result.status);

    if (result.status !== 0) {
        process.exit(result.status);
    }
}

run("npx", ["lint-staged"]);

// git-info.json is imported by DashboardView.vue and its tests; it is
// normally produced by the prebuild/pretypecheck hooks, so regenerate it
// here to keep a bare `npm run test:coverage` (and this hook) working.
run("node", ["scripts/update-version.cjs"]);

// vue-tsc, before the tests: CI gates on `npm run typecheck` and nothing local did, so a
// type error - a prop shape that drifted, an index that can be undefined - passed every hook
// and failed the build instead. ~18s, and it catches what neither eslint nor vitest can:
// vitest transpiles without checking types, and eslint is not type-aware here.
// update-version.cjs above already wrote git-info.json, which pretypecheck would regenerate.
run("npx", ["vue-tsc", "--noEmit", "-p", "tsconfig.json"]);

// test:unit, not test:coverage: the V8 coverage pass adds time on every commit and
// nothing local consumes the report. CI still runs test:coverage and uploads it.
run("npm", ["run", "test:unit"]);
