// All Rounder Dashboard V1

document.addEventListener("DOMContentLoaded", () => {

    console.log("All Rounder Dashboard V1 loaded.");

    // Current time
    const timeBox = document.createElement("p");

    timeBox.id = "dashboard-time";

    timeBox.style.textAlign = "center";
    timeBox.style.marginTop = "15px";
    timeBox.style.color = "#94a3b8";

    document.querySelector(".hero").appendChild(timeBox);

    function updateTime() {
        const now = new Date();

        timeBox.textContent =
            "Dashboard time: " +
            now.toLocaleTimeString();
    }

    updateTime();

    setInterval(updateTime, 1000);


    // Dashboard loaded message
    console.log("🤖 All Rounder is ready!");
});
