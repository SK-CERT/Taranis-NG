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

run("npm", ["run", "test:coverage"]);
