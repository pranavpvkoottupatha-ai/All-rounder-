// ========================================
// ALL ROUNDER DASHBOARD V2
// ========================================

document.addEventListener("DOMContentLoaded", () => {

    // -----------------------------
    // Page navigation
    // -----------------------------

    const navButtons = document.querySelectorAll(".nav-btn");
    const pages = document.querySelectorAll(".page");

    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");

    const titles = {
        dashboard: ["Dashboard", "Welcome to All Rounder"],
        moderation: ["Moderation", "Manage moderation features"],
        antispam: ["Anti-Spam", "Configure spam protection"],
        commands: ["Commands", "Available bot commands"],
        settings: ["Settings", "Bot configuration"]
    };

    function showPage(pageName) {

        pages.forEach(page => {
            page.classList.remove("active");
        });

        const selectedPage = document.getElementById(pageName);

        if (selectedPage) {
            selectedPage.classList.add("active");
        }

        navButtons.forEach(button => {
            button.classList.remove("active");

            if (button.dataset.page === pageName) {
                button.classList.add("active");
            }
        });

        if (titles[pageName]) {
            pageTitle.textContent = titles[pageName][0];
            pageSubtitle.textContent = titles[pageName][1];
        }

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }


    navButtons.forEach(button => {

        button.addEventListener("click", () => {

            showPage(button.dataset.page);

        });

    });


    // -----------------------------
    // Quick action buttons
    // -----------------------------

    const quickButtons =
        document.querySelectorAll("[data-page-target]");

    quickButtons.forEach(button => {

        button.addEventListener("click", () => {

            showPage(button.dataset.pageTarget);

        });

    });


    // -----------------------------
    // Live clock
    // -----------------------------

    const timeElement =
        document.getElementById("currentTime");

    function updateClock() {

        const now = new Date();

        timeElement.textContent =
            now.toLocaleTimeString();

    }

    updateClock();

    setInterval(updateClock, 1000);


    // -----------------------------
    // Refresh button
    // -----------------------------

    const refreshButton =
        document.getElementById("refreshBtn");

    refreshButton.addEventListener("click", () => {

        showToast("🔄 Dashboard refreshed!");

        updateClock();

    });


    // -----------------------------
    // Anti-spam settings
    // -----------------------------

    const saveSpam =
        document.getElementById("saveSpam");

    const spamToggle =
        document.getElementById("spamToggle");

    const spamLimit =
        document.getElementById("spamLimit");

    const spamTime =
        document.getElementById("spamTime");


    saveSpam.addEventListener("click", () => {

        const enabled = spamToggle.checked;

        const limit = spamLimit.value;

        const time = spamTime.value;

        localStorage.setItem(
            "spamEnabled",
            enabled
        );

        localStorage.setItem(
            "spamLimit",
            limit
        );

        localStorage.setItem(
            "spamTime",
            time
        );

        showToast(
            "✅ Anti-spam settings saved!"
        );

    });


    // -----------------------------
    // Load saved settings
    // -----------------------------

    const saved
