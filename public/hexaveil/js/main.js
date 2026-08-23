// Main script – nav, smooth scroll, burger menu, scroll animations

document.addEventListener("DOMContentLoaded", () => {
  const burger = document.getElementById("burger");
  const nav = document.querySelector(".nav");

  if (!burger || !nav) return;

  // Toggle mobile menu
  burger.addEventListener("click", (e) => {
    e.stopPropagation();
    burger.classList.toggle("open");
    nav.classList.toggle("open");
  });

  // Close menu on outside click
  document.addEventListener("click", (e) => {
    if (
      nav.classList.contains("open") &&
      !nav.contains(e.target) &&
      !burger.contains(e.target)
    ) {
      burger.classList.remove("open");
      nav.classList.remove("open");
    }
  });

  // Smooth scroll for internal links + close menu
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const targetId = link.getAttribute("href").substring(1);
      const target = document.getElementById(targetId);
      if (target) {
        e.preventDefault();
        const headerOffset = 70;
        const elementPosition = target.getBoundingClientRect().top;
        const offsetPosition =
          elementPosition + window.pageYOffset - headerOffset;
        window.scrollTo({ top: offsetPosition, behavior: "smooth" });
        // close mobile menu
        if (nav.classList.contains("open")) {
          burger.classList.remove("open");
          nav.classList.remove("open");
        }
      }
    });
  });

  // IntersectionObserver for scroll animations
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    { threshold: 0.1 },
  );

  document
    .querySelectorAll(".animate-on-scroll")
    .forEach((el) => observer.observe(el));
});

// ============ COUNTER ANIMATION FOR STATS ============
function animateCounter(el, target, suffix, duration = 2000) {
  const start = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const current = Math.floor(eased * target);

    el.textContent = current + suffix;

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = target + suffix;
    }
  }

  requestAnimationFrame(update);
}

function parseStatNumber(text) {
  const match = text.match(/^([\d.]+)(.*)$/);
  if (!match) return { num: 0, suffix: text };
  return {
    num: parseFloat(match[1]),
    suffix: match[2],
  };
}

function initStatsCounter() {
  const statsSection = document.querySelector(".stats-section");
  if (!statsSection) return;

  const statNumbers = statsSection.querySelectorAll(".stat-number");
  if (!statNumbers.length) return;

  // Store original text for each element
  statNumbers.forEach((el) => {
    const { num, suffix } = parseStatNumber(el.textContent);
    el.dataset.target = num;
    el.dataset.suffix = suffix;
    el.textContent = "0" + suffix;
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const numbers = entry.target.querySelectorAll(".stat-number");
          numbers.forEach((el) => {
            const target = parseFloat(el.dataset.target);
            const suffix = el.dataset.suffix;
            animateCounter(el, target, suffix);
          });
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 },
  );

  observer.observe(statsSection);
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initStatsCounter);
} else {
  initStatsCounter();
}
