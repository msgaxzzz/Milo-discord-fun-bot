document.addEventListener('DOMContentLoaded', () => {
  const revealTargets = document.querySelectorAll('.animate-on-scroll');

  // Scroll reveal
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });

    revealTargets.forEach((el) => observer.observe(el));
  } else {
    revealTargets.forEach((el) => el.classList.add('is-visible'));
  }

  // Copy button
  const copyBtn = document.querySelector('.copy-btn');
  const codeBlock = document.querySelector('.card-code code');
  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const fallback = document.createElement('textarea');
    fallback.value = text;
    fallback.setAttribute('readonly', '');
    fallback.style.position = 'absolute';
    fallback.style.left = '-9999px';
    document.body.appendChild(fallback);
    fallback.select();
    document.execCommand('copy');
    fallback.remove();
  };

  const setCopyState = (label, stateClass) => {
    copyBtn.innerText = label;
    copyBtn.classList.toggle('copied', stateClass === 'copied');
    copyBtn.classList.toggle('copy-failed', stateClass === 'failed');
  };

  if (copyBtn && codeBlock) {
    copyBtn.addEventListener('click', async () => {
      try {
        await copyText(codeBlock.innerText);
        setCopyState('Copied!', 'copied');
      } catch (error) {
        console.error('Failed to copy quick start snippet.', error);
        setCopyState('Copy failed', 'failed');
      }

      window.setTimeout(() => {
        setCopyState('Copy', '');
      }, 2000);
    });
  }

  // Scroll spy
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.topnav a');
  const updateActiveLink = () => {
    let current = '';

    sections.forEach((section) => {
      if (window.scrollY >= section.offsetTop - 120) {
        current = section.getAttribute('id');
      }
    });

    navLinks.forEach((link) => {
      link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
    });
  };

  updateActiveLink();
  window.addEventListener('scroll', updateActiveLink, { passive: true });
});
