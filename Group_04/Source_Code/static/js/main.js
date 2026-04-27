/* ============================================================
   I-Care – Main JS (global utilities)
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
    // Smooth-scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', e => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) target.scrollIntoView({ behavior: 'smooth' });
        });
    });
});
