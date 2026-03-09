/**
 * Handles authentication form submissions (login, register, etc.) via AJAX.
 * Manages loading states, toasts, and redirection.
 */
class AuthFormHandler {
    /**
     * @param {string} formId - ID of the form element
     * @param {string} buttonId - ID of the submit button
     * @param {string} textId - ID of the button text span
     * @param {string} loaderId - ID of the button loader span
     * @param {string} sectionLoaderColor - Tailwind class for the section loader color
     */
    constructor(formId, buttonId, textId, loaderId, sectionLoaderColor = 'fill-emerald-600') {
        this.form = document.getElementById(formId);
        this.button = document.getElementById(buttonId);
        this.buttonText = document.getElementById(textId);
        this.buttonLoader = document.getElementById(loaderId);
        
        if (!this.form) return;

        this.loader = new SectionLoaderManager(formId, sectionLoaderColor, 0.5);
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.initPasswordToggles();
    }

    initPasswordToggles() {
        this.form.querySelectorAll('.password-toggle').forEach(icon => {
            icon.addEventListener('click', function() {
                const input = this.previousElementSibling;
                if (input.type === 'password') {
                    input.type = 'text';
                    this.classList.remove('fa-eye');
                    this.classList.add('fa-eye-slash');
                } else {
                    input.type = 'password';
                    this.classList.remove('fa-eye-slash');
                    this.classList.add('fa-eye');
                }
            });
        });
    }

    setLoading(isLoading) {
        if (isLoading) {
            this.loader.showLoader();
            if (this.button) this.button.disabled = true;
            if (this.buttonText) this.buttonText.classList.add('hidden');
            if (this.buttonLoader) this.buttonLoader.classList.remove('hidden');
        } else {
            this.loader.hideLoader();
            if (this.button) this.button.disabled = false;
            if (this.buttonText) this.buttonText.classList.remove('hidden');
            if (this.buttonLoader) this.buttonLoader.classList.add('hidden');
        }
    }

    handleSubmit(e) {
        e.preventDefault();
        this.setLoading(true);

        const formData = new FormData(this.form);
        fetch(this.form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            this.setLoading(false);

            window.toastManager.buildToast()
                .setMessage(data.message)
                .setType(data.success ? 'success' : 'danger')
                .setPosition('top-right')
                .setDuration(5000)
                .show();

            if (data.success) {
                if (data.redirect_url) {
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1500);
                }
            } else if (data.fields) {
                this.updateFields(data.fields);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.setLoading(false);
            window.toastManager.buildToast()
                .setMessage('An unexpected error occurred. Please try again.')
                .setType('danger')
                .setPosition('top-right')
                .setDuration(5000)
                .show();
        });
    }

    updateFields(fields) {
        for (const [name, value] of Object.entries(fields)) {
            const input = this.form.querySelector(`[name="${name}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = value;
                } else {
                    input.value = value;
                }
            }
        }
    }
}
