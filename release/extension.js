// Built using vscode.py
const vscode = require("vscode");
const { spawn, execSync } = require("child_process");
const path = require("path");
const pythonExtensionPath = path.join(__dirname, process.platform.startsWith("win") ? "extension.exe" : "extension");

const wslib = require("ws");
const fs = require("fs");
let ws;

function commandCallback(command) {
  if (ws && ws.readyState == 1) {
    ws.send(JSON.stringify({ type: 1, name: command }));
  } else {
    setTimeout(() => commandCallback(command), 50);
  }
}


function registerCommands(context) {
	
  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.start", () =>
        commandCallback("start")
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.reload", () =>
        commandCallback("reload")
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.login", () =>
        commandCallback("login")
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.change", () =>
        commandCallback("change")
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.buildAndRun", () =>
        commandCallback("buildAndRun")
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nsuts.submit", () =>
        commandCallback("submit")
    )
  );

}


function activate(context) {
  registerCommands(context);
  let py = spawn(pythonExtensionPath, ["--run-webserver"]);
  let webviews = {};
  let progressRecords = {};

  py.stdout.on("data", (data) => {
    let mes = data.toString().trim();
    if (ws) {
      console.log(mes);
    }
    let arr = mes.split(" ");
    if (arr.length == 3 && arr[arr.length - 1].startsWith("ws://localhost:")) {
      ws = new wslib.WebSocket(arr[arr.length - 1]);
      console.log("Connecting to " + arr[arr.length - 1]);
      ws.on("open", () => {
        console.log("Connected!");
        ws.send(JSON.stringify({ type: 2, event: "activate" }));
      });
      ws.on("message", async (message) => {
        console.log("received: %s", message.toString());
        try {
          let data = JSON.parse(message.toString());
          if (data.type == 1) {
            eval(data.code);
          } else if (data.type == 2) {
            eval(
              data.code +
                `.then(res => ws.send(JSON.stringify({ type: 3, res, uuid: "${data.uuid}" })));`
            );
          } else if (data.type == 3) {
            let res = eval(data.code);
            ws.send(JSON.stringify({ type: 3, res, uuid: data.uuid }));
          }
        } catch (e) {
          console.log(e);
        }
      });

      ws.on("close", () => {
        console.log("Connection closed!");
      });
    }
  });
  py.stderr.on("data", (data) => {
    console.error(`An Error occurred in the python script: ${data}`);
  });
}

function deactivate() {}

module.exports = { activate, deactivate };
