document.addEventListener('DOMContentLoaded', () => {
    const input = document.querySelector('#search-input input[name="q"]');
    const form = document.querySelector('#search-input form');
    const cancel = document.querySelector('#cancel-search');
    const paginator = document.querySelector('.pagination');
    const spinner = document.querySelector('#spinner');
    const authenticator = document.querySelector('input[name="_authenticator"]');

    // Validate required elements
    if (!input || !form || !cancel || !spinner || !authenticator) {
        console.error('One or more required DOM elements are missing:', {
            input, form, cancel, spinner, authenticator
        });
        return;
    }

    // Show cancel button if input has a value
    if (input.value && input.value.trim() !== '') {
        cancel.classList.remove('d-none');
        cancel.classList.add('d-block');
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        spinner.classList.remove('d-none');
        spinner.classList.add('d-block');
        var url = $('base').attr('href');
        console.log('Base URL:', url);
        if (url) {
            var cleaned_url = url.split('=')[0] + '=0';
            console.log('Cleaned URL:', cleaned_url);
        }

        $.ajax({
            url: cleaned_url,
            method: 'GET',
            data: {
                q: input.value.trim(),
            },
            cache: false,
            async: true,
            success: function(result) {
                try {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(result, 'text/html');
                    const newContent = doc.querySelector('#pdf-files');
                    
                    if (newContent) {
                        document.querySelector('#pdf-files').innerHTML = newContent.innerHTML;
                    } else {
                        console.error('No #pdf-files element found in server response');
                        return;
                    }

                    // Update cancel button visibility
                    if (input.value.trim() !== '') {
                        cancel.classList.remove('d-none');
                        cancel.classList.add('d-block');
                        paginator.classList.add("d-none");
                    } else {
                        cancel.classList.remove('d-block');
                        cancel.classList.add('d-none');
                        paginator.classList.remove("d-none");
                    }
                } catch (parseError) {
                    console.error('Error parsing server response:', parseError);
                }
            },
            error: function(xhr, status, error) {
                console.error('AJAX error:', status, error, xhr.responseText);
            },
            complete: function() {
                spinner.classList.remove('d-block');
                spinner.classList.add('d-none');
            }
        });
    });

    cancel.addEventListener('click', () => {
        input.value = '';
        form.dispatchEvent(new Event('submit'));
        cancel.classList.remove('d-block');
        cancel.classList.add('d-none');
    });
});