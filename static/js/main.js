$(document).ready(function() {
    $('a[href*="#"]').on('click', function(e) {
        if (this.hash !== '') {
            e.preventDefault();
            const hash = this.hash;
            $('html, body').animate({
                scrollTop: $(hash).offset().top
            }, 800);
        }
    });

    const currentLocation = window.location.pathname;
    $('.navbar-nav .nav-link').each(function() {
        const linkPath = $(this).attr('href');
        if (currentLocation === linkPath) {
            $(this).addClass('active');
        }
    });

    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    function formatNumber(num) {
        return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1 ');
    }

    $('#searchForm').on('submit', function(e) {
        const query = $('#query').val().trim();
        if (!query) {
            e.preventDefault();
            alert('Введите поисковый запрос');
        }
    });

    $(window).on('load', function() {
        $('.spinner-overlay').fadeOut('slow');
    });
});

function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    alert('Скопировано в буфер обмена!');
}

function sortTable(n) {
    const table = document.getElementById("vacanciesTable");
    let switching = true;
    let direction = "asc";
    let switchcount = 0;

    while (switching) {
        switching = false;
        const rows = table.rows;

        for (let i = 1; i < (rows.length - 1); i++) {
            let shouldSwitch = false;
            const x = rows[i].getElementsByTagName("TD")[n];
            const y = rows[i + 1].getElementsByTagName("TD")[n];

            if (direction === "asc") {
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            } else {
                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            }
        }

        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchcount++;
        } else {
            if (switchcount === 0 && direction === "asc") {
                direction = "desc";
                switching = true;
            }
        }
    }
}