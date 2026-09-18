document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
  
    searchInput.addEventListener('input', function() {
        const query = searchInput.value.trim();
  
        if (query.length > 0) {
            fetch(`/search/services/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    console.log('Data received:', data);
                    if (data.length > 0) {
                        data.forEach(item => {
                            const li = document.createElement('li');
                            li.textContent = item.name;
                            li.addEventListener('click', function() {
                                window.location.href = item.slug;
                            });
                            searchResults.appendChild(li);
                        });
                        searchResults.style.display = 'block';
                    } else {
                        searchResults.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error fetching search results:', error);
                    searchResults.style.display = 'none';
                });
        } else {
            searchResults.style.display = 'none';
        }
    });
  
    document.addEventListener('click', function(event) {
        if (!searchInput.contains(event.target) && !searchResults.contains(event.target)) {
            searchResults.style.display = 'none';
        }
    });
  });
  