// Ждем полной загрузки DOM
document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  // ========================
  // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
  // ========================

  // Простая реализация шума (Simplex noise упрощенная версия)
  class SimplexNoise {
    constructor() {
      this.grad3 = [
        [1, 1, 0],
        [-1, 1, 0],
        [1, -1, 0],
        [-1, -1, 0],
        [1, 0, 1],
        [-1, 0, 1],
        [1, 0, -1],
        [-1, 0, -1],
        [0, 1, 1],
        [0, -1, 1],
        [0, 1, -1],
        [0, -1, -1],
      ];

      this.p = [];
      for (let i = 0; i < 256; i++) {
        this.p[i] = Math.floor(Math.random() * 256);
      }

      this.perm = [];
      for (let i = 0; i < 512; i++) {
        this.perm[i] = this.p[i & 255];
      }
    }

    dot3(g, x, y, z) {
      return g[0] * x + g[1] * y + g[2] * z;
    }

    fade(t) {
      return t * t * t * (t * (t * 6 - 15) + 10);
    }

    lerp(a, b, t) {
      return a + t * (b - a);
    }

    noise3D(x, y, z) {
      const X = Math.floor(x) & 255;
      const Y = Math.floor(y) & 255;
      const Z = Math.floor(z) & 255;

      const xf = x - Math.floor(x);
      const yf = y - Math.floor(y);
      const zf = z - Math.floor(z);

      const u = this.fade(xf);
      const v = this.fade(yf);
      const w = this.fade(zf);

      const p = this.perm;
      const g = this.grad3;

      const aaa = p[p[p[X] + Y] + Z];
      const aba = p[p[p[X] + Y + 1] + Z];
      const aab = p[p[p[X] + Y] + Z + 1];
      const abb = p[p[p[X] + Y + 1] + Z + 1];
      const baa = p[p[p[X + 1] + Y] + Z];
      const bba = p[p[p[X + 1] + Y + 1] + Z];
      const bab = p[p[p[X + 1] + Y] + Z + 1];
      const bbb = p[p[p[X + 1] + Y + 1] + Z + 1];

      const x1 = this.lerp(
        this.dot3(g[aaa % 12], xf, yf, zf),
        this.dot3(g[baa % 12], xf - 1, yf, zf),
        u,
      );
      const x2 = this.lerp(
        this.dot3(g[aba % 12], xf, yf - 1, zf),
        this.dot3(g[bba % 12], xf - 1, yf - 1, zf),
        u,
      );
      const y1 = this.lerp(x1, x2, v);

      const x3 = this.lerp(
        this.dot3(g[aab % 12], xf, yf, zf - 1),
        this.dot3(g[bab % 12], xf - 1, yf, zf - 1),
        u,
      );
      const x4 = this.lerp(
        this.dot3(g[abb % 12], xf, yf - 1, zf - 1),
        this.dot3(g[bbb % 12], xf - 1, yf - 1, zf - 1),
        u,
      );
      const y2 = this.lerp(x3, x4, v);

      return this.lerp(y1, y2, w);
    }
  }

  // Класс для управления анимированным фоном
  class ParticleBackground {
    constructor(options = {}) {
      // Настройки по умолчанию
      this.settings = {
        particleCount: options.particleCount || 800,
        rangeY: options.rangeY || 300,
        rangeX: options.rangeX || 100,
        baseHue: options.baseHue || 220,
        rangeSpeed: options.rangeSpeed || 1.5,
        backgroundColor: options.backgroundColor || "#000000",
        container: options.container || document.body,
        spread: options.spread || "full", // 'full' или 'center'
      };

      // Константы
      this.TWO_PI = 2 * Math.PI;
      this.STRIDE = 9;
      this.isMobile = window.innerWidth < 768;

      // На мобильных резко снижаем число частиц: полный набор на dpr=3 во весь
      // экран не успевает отрисоваться за кадр на реальном устройстве → лаги.
      if (this.isMobile) {
        this.settings.particleCount = Math.min(this.settings.particleCount, 150);
      }

      // Инициализация
      this.init();
    }

    init() {
      // Проверяем, что контейнер существует
      if (!this.settings.container) {
        console.error("Контейнер не найден!");
        return;
      }

      // Создаем canvas
      this.canvas = document.createElement("canvas");
      this.container = this.settings.container;
      this.container.appendChild(this.canvas);

      // Настройка размеров
      this.resize();

      // Получаем контекст
      this.ctx = this.canvas.getContext("2d");
      if (!this.ctx) {
        console.error("Не удалось получить контекст canvas!");
        return;
      }

      this.ctx.lineCap = "round";

      // Инициализация шума
      this.noise = new SimplexNoise();

      // Создание частиц
      this.createParticles();

      // Переменные для анимации
      this.tick = 0;
      this.animationId = null;
      this.isRunning = true;

      // Уважение prefers-reduced-motion: не запускаем анимацию вовсе
      this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (this.reducedMotion) {
        this.isRunning = false;
        return;
      }

      // Обработчик изменения размера окна
      this.resizeHandler = this.resize.bind(this);
      window.addEventListener("resize", this.resizeHandler);

      // Запуск анимации
      this.animate();
    }

    resize() {
      // Капим dpr на 2: на телефонах (dpr=3) буфер canvas во весь экран
      // становится гигантским и убивает производительность.
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = window.innerWidth;
      const height = window.innerHeight;

      this.width = width;
      this.height = height;
      this.dpr = dpr;
      this.centerX = width * 0.5;
      this.centerY = height * 0.5;

      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;

      if (this.ctx) {
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        this.ctx.lineCap = "round";
      }
    }

    createParticles() {
      const total = this.settings.particleCount * this.STRIDE;
      this.particles = new Float32Array(total);

      for (let i = 0; i < total; i += this.STRIDE) {
        // Распределяем частицы по всему экрану
        let x, y;

        if (this.settings.spread === "full") {
          // Частицы по всему экрану
          x = Math.random() * this.width;
          y = Math.random() * this.height;
        } else {
          // Частицы в центре с разбросом
          x = this.centerX + this.randomRange(this.settings.rangeX || 100);
          y = this.centerY + this.randomRange(this.settings.rangeY);
        }

        this.particles[i] = x; // x
        this.particles[i + 1] = y; // y
        this.particles[i + 2] = 0; // offsetX
        this.particles[i + 3] = 0; // offsetY
        this.particles[i + 4] = Math.random() * 100; // time (случайное начальное время)
        this.particles[i + 5] = 50 + Math.random() * 150; // lifetime
        this.particles[i + 6] = Math.random() * this.settings.rangeSpeed; // speed
        this.particles[i + 7] = 1 + Math.random() * 2; // lineWidth
        this.particles[i + 8] = this.settings.baseHue + Math.random() * 100; // hue
      }
    }

    randomRange(max) {
      return max - Math.random() * 2 * max;
    }

    lerp(a, b, t) {
      return (1 - t) * a + t * b;
    }

    sawtooth(value, period) {
      const half = 0.5 * period;
      return Math.abs(((value + half) % period) - half) / half;
    }

    resetParticle(index) {
      const i = index;

      // При сбросе распределяем по всему экрану
      if (this.settings.spread === "full") {
        this.particles[i] = Math.random() * this.width;
        this.particles[i + 1] = Math.random() * this.height;
      } else {
        this.particles[i] =
          this.centerX + this.randomRange(this.settings.rangeX || 100);
        this.particles[i + 1] =
          this.centerY + this.randomRange(this.settings.rangeY);
      }

      this.particles[i + 2] = 0;
      this.particles[i + 3] = 0;
      this.particles[i + 4] = 0;
      this.particles[i + 5] = 50 + Math.random() * 150;
      this.particles[i + 6] = Math.random() * this.settings.rangeSpeed;
      this.particles[i + 7] = 1 + Math.random() * 2;
      this.particles[i + 8] = this.settings.baseHue + Math.random() * 100;
    }

    animate() {
      if (!this.isRunning || !this.ctx) {
        return;
      }

      const ctx = this.ctx;
      const w = this.width;
      const h = this.height;
      const total = this.settings.particleCount * this.STRIDE;

      this.tick++;

      // Очистка canvas (прозрачный фон — не закрашиваем страницу чёрным)
      ctx.clearRect(0, 0, w, h);

      // Обновление каждой частицы
      for (let i = 0; i < total; i += this.STRIDE) {
        const x = this.particles[i];
        const y = this.particles[i + 1];

        // Генерация направления с помощью шума
        const angle =
          this.noise.noise3D(x * 0.00125, y * 0.00125, this.tick * 0.0005) *
          3 *
          this.TWO_PI;

        const offsetX = this.lerp(this.particles[i + 2], Math.cos(angle), 0.5);
        const offsetY = this.lerp(this.particles[i + 3], Math.sin(angle), 0.5);

        const time = this.particles[i + 4];
        const lifetime = this.particles[i + 5];
        const speed = this.particles[i + 6];

        const newX = x + offsetX * speed;
        const newY = y + offsetY * speed;

        const lineWidth = this.particles[i + 7];
        const hue = this.particles[i + 8];

        // Отрисовка линии
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = `hsla(${hue}, 100%, 60%, ${this.sawtooth(time, lifetime)})`;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(newX, newY);
        ctx.stroke();

        // Обновление свойств частицы
        this.particles[i] = newX;
        this.particles[i + 1] = newY;
        this.particles[i + 2] = offsetX;
        this.particles[i + 3] = offsetY;
        this.particles[i + 4] = time + 1;

        // Сброс частицы при выходе за границы
        if (
          newX > w ||
          newX < 0 ||
          newY > h ||
          newY < 0 ||
          time + 1 > lifetime
        ) {
          this.resetParticle(i);
        }
      }

      // Эффект свечения (только для десктопа)
      if (!this.isMobile) {
        ctx.save();
        ctx.filter = "blur(8px) brightness(200%)";
        ctx.globalCompositeOperation = "lighter";
        ctx.drawImage(this.canvas, 0, 0, w, h);
        ctx.restore();
      }

      // Продолжаем анимацию
      this.animationId = requestAnimationFrame(this.animate.bind(this));
    }

    destroy() {
      this.isRunning = false;
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
        this.animationId = null;
      }
      window.removeEventListener("resize", this.resizeHandler);
      if (this.canvas && this.canvas.parentNode) {
        this.canvas.parentNode.removeChild(this.canvas);
      }
    }
  }

  // ========================
  // ИНИЦИАЛИЗАЦИЯ
  // ========================

  // Находим контейнер
  const container = document.getElementById("particle-container");

  if (!container) {
    console.error("Элемент #particle-container не найден!");
    return;
  }

  // Создаем экземпляр с настройками
  const background = new ParticleBackground({
    container: container,
    particleCount: 500, // Частицы для заполнения экрана
    rangeY: 300, // Вертикальный разброс
    rangeX: 200, // Горизонтальный разброс (для режима 'center')
    baseHue: 220, // Базовый цвет
    rangeSpeed: 1.5, // Скорость
    backgroundColor: "transparent", // Прозрачный фон — не перекрываем страницу
    spread: "full", // 'full' - по всему экрану, 'center' - в центре
  });

  // Сохраняем в глобальную область для отладки
  window.particleBackground = background;

  // Останавливаем анимацию при уходе со страницы для экономии ресурсов
  document.addEventListener("visibilitychange", function () {
    if (background.reducedMotion) return; // reduced-motion: анимацию не перезапускаем
    if (document.hidden) {
      background.isRunning = false;
      if (background.animationId) {
        cancelAnimationFrame(background.animationId);
        background.animationId = null;
      }
    } else {
      background.isRunning = true;
      if (!background.animationId) {
        background.animate();
      }
    }
  });
});
