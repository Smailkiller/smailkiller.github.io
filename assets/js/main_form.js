/*
    Solid State by HTML5 UP
    html5up.net | @ajlkn
    Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

    var $window = $(window),
        $body = $('body'),
        $header = $('#header'),
        $banner = $('#banner');

    // Breakpoints.
    breakpoints({
        xlarge: '(max-width: 1680px)',
        large: '(max-width: 1280px)',
        medium: '(max-width: 980px)',
        small: '(max-width: 736px)',
        xsmall: '(max-width: 480px)'
    });

    // Play initial animations on page load.
    $window.on('load', function() {
        window.setTimeout(function() {
            $body.removeClass('is-preload');
        }, 100);
    });

    // Header.
    if ($banner.length > 0 && $header.hasClass('alt')) {
        $window.on('resize', function() { $window.trigger('scroll'); });

        $banner.scrollex({
            bottom: $header.outerHeight(),
            terminate: function() { $header.removeClass('alt'); },
            enter: function() { $header.addClass('alt'); },
            leave: function() { $header.removeClass('alt'); }
        });
    }

    // Menu.
    var $menu = $('#menu');

    $menu._locked = false;

    $menu._lock = function() {
        if ($menu._locked)
            return false;
        $menu._locked = true;
        window.setTimeout(function() {
            $menu._locked = false;
        }, 350);
        return true;
    };

    $menu._show = function() {
        if ($menu._lock())
            $body.addClass('is-menu-visible');
    };

    $menu._hide = function() {
        if ($menu._lock())
            $body.removeClass('is-menu-visible');
    };

    $menu._toggle = function() {
        if ($menu._lock())
            $body.toggleClass('is-menu-visible');
    };

    $menu
        .appendTo($body)
        .on('click', function(event) {
            event.stopPropagation();
            $menu._hide();
        })
        .find('.inner')
            .on('click', '.close', function(event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                $menu._hide();
            })
            .on('click', function(event) {
                event.stopPropagation();
            })
            .on('click', 'a', function(event) {
                var href = $(this).attr('href');
                event.preventDefault();
                event.stopPropagation();
                $menu._hide();
                window.setTimeout(function() {
                    window.location.href = href;
                }, 350);
            });

    $body
        .on('click', 'a[href="#menu"]', function(event) {
            event.stopPropagation();
            event.preventDefault();
            $menu._toggle();
        })
        .on('keydown', function(event) {
            if (event.keyCode == 27)
                $menu._hide();
        });

})(jQuery);

// === Contact Form Telegram Integration ===
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("contact-form");

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const name = document.getElementById("name").value.trim();
      const contact = document.getElementById("contact").value.trim();
      const message = document.getElementById("message").value.trim();

      const text = `📝 Новое сообщение с сайта:\n👤 Имя: ${name}\n📬 Связь: ${contact}\n💬 Сообщение: ${message}`;

      fetch("http://marichevai/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, contact, message })
      })
      .then(response => {
        if (response.ok) {
          alert("Сообщение успешно отправлено!");
          form.reset();
        } else {
          alert("Ошибка при отправке. Попробуйте позже.");
        }
      })
      .catch(error => {
        console.error(error);
        alert("Ошибка сети. Проверьте подключение.");
      });
    });
  }
});