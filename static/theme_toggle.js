// On page load: set theme based on saved preference
window.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.body.classList.add('dark');
    document.getElementById('theme-toggle').textContent = '☀️';
  } else {
    document.body.classList.remove('dark');
    document.getElementById('theme-toggle').textContent = '🌙';
  }
});

// On button click: toggle theme and save preference
document.getElementById('theme-toggle').addEventListener('click', function() {
  document.body.classList.toggle('dark');
  if (document.body.classList.contains('dark')) {
    this.textContent = '☀️';
    localStorage.setItem('theme', 'dark');
  } else {
    this.textContent = '🌙';
    localStorage.setItem('theme', 'light');
  }
});
