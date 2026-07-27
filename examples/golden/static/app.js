(() => {
  document.addEventListener("todo:created", () => {
    const input = document.querySelector("#new-todo");
    if (input instanceof HTMLInputElement) {
      input.value = "";
      input.focus();
    }
    const errors = document.querySelector("#todo-form-errors");
    if (errors) {
      errors.replaceChildren();
    }
  });

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }
    const button = event.target.closest("#stream-demo");
    const output = document.querySelector("#stream-output");
    if (!(button instanceof HTMLButtonElement) || !(output instanceof HTMLOutputElement)) {
      return;
    }
    button.disabled = true;
    output.textContent = "";
    const stream = new EventSource("/todos/stream");
    let completed = false;

    stream.addEventListener("token", (event) => {
      const message = JSON.parse(event.data);
      if (typeof message.token === "string") {
        output.textContent += message.token;
      }
    });

    stream.addEventListener("done", () => {
      completed = true;
      button.disabled = false;
    });

    stream.addEventListener("error", () => {
      stream.close();
      button.disabled = false;
      if (!completed) {
        output.textContent = "The stream stopped. Try again.";
      }
    });
  });
})();
