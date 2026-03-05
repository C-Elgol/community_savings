/**
 * Manages Flowbite modals with a builder pattern for flexible configuration.
 * Provides methods to create, show, and close modals with customizable types, content, and buttons.
 * Supports internationalization with gettext.
 * @class
 */
class SweetModalManager {
    constructor() {
        this.modal = null;
        this.modalInstance = null;
        this.resolveCallback = null;
        this.rejectCallback = null;
        this.isClosing = false; // Prevent recursive calls
    }

    /**
     * Retrieves the style configuration for a given modal type.
     * @param {string} type - The type of modal ('info', 'confirm', 'error', 'warning', 'success').
     * @returns {Object} The style configuration for the specified type, including outline red style for retry button.
     */
    getModalStyles(type) {
        const styles = {
            info: {
                icon: `<svg class="mx-auto mb-4 text-secondary-600 w-12 h-12" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 11h2v5m-2 0h4m-2.592-8.5h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                </svg>`,
                buttonClass: "btn-secondary cursor-pointer",
                retryButtonClass: "text-red-600 border border-red-600 bg-transparent hover:bg-red-600 hover:text-white focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                title: gettext("Information")
            },
            confirm: {
                icon: `<svg class="mx-auto mb-4 text-gray-400 w-12 h-12" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 20">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                </svg>`,
                confirmButtonClass: "text-white bg-red-600 hover:bg-red-800 focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                cancelButtonClass: "py-2.5 px-5 ms-3 text-sm font-medium text-gray-900 focus:outline-none bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-blue-700 focus:z-10 focus:ring-4 focus:ring-gray-100 cursor-pointer",
                retryButtonClass: "text-red-600 border border-red-600 bg-transparent hover:bg-red-600 hover:text-white focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                title: gettext("Confirm action")
            },
            error: {
                icon: `<svg class="mx-auto mb-4 text-red-600 w-20 h-20" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m15 9-6 6m0-6 6 6m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                </svg>`,
                buttonClass: "text-white bg-red-600 hover:bg-red-800 focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                retryButtonClass: "text-red-600 border border-red-600 bg-transparent hover:bg-red-600 hover:text-white focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                title: gettext("Error")
            },
            warning: {
                icon: `<svg class="mx-auto mb-4 text-orange-400 w-12 h-12" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 20">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                </svg>`,
                buttonClass: "text-white bg-orange-600 hover:bg-orange-800 focus:ring-4 focus:outline-none focus:ring-orange-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                retryButtonClass: "text-red-600 border border-red-600 bg-transparent hover:bg-red-600 hover:text-white focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                title: gettext("Warning")
            },
            success: {
                icon: `<svg class="mx-auto mb-4 text-green-600 w-20 h-20" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.5 11.5 11 14l4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                </svg>`,
                buttonClass: "text-white bg-green-600 hover:bg-green-800 focus:ring-4 focus:outline-none focus:ring-green-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                retryButtonClass: "text-red-600 border border-red-600 bg-transparent hover:bg-red-600 hover:text-white focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm inline-flex items-center px-5 py-2.5 text-center cursor-pointer",
                title: gettext("Success")
            }
        };
        return styles[type] || styles.info;
    }

    /**
     * Creates a new ModalBuilder instance to configure a modal.
     * @returns {ModalBuilder} A new ModalBuilder instance.
     * @example
     * sweetModalManager.buildModal()
     *     .setType('error')
     *     .setTitle('Custom Error')
     *     .setContent('An error occurred')
     *     .setButtonType('retry')
     *     .setConfirmText('Try Again')
     *     .setShowTitle(true)
     *     .show()
     *     .then(result => console.log(result));
     */
    buildModal() {
        return new ModalBuilder(this);
    }

    /**
     * Creates the modal DOM element and initializes the Modal instance.
     * @private
     * @param {Object} config - The modal configuration.
     * @param {string} config.type - The modal type.
     * @param {string} config.title - Custom title for the modal (optional).
     * @param {string} config.content - The modal content (HTML or text).
     * @param {string} config.confirmText - Text for the confirm/retry button.
     * @param {string} config.cancelText - Text for the cancel button.
     * @param {string} config.customContentClass - Additional classes for the content div.
     * @param {string} config.customTitleClass - Additional classes for the title.
     * @param {string} config.okButtonClass - Custom class for the OK button.
     * @param {string} config.confirmButtonClass - Custom class for the confirm button.
     * @param {string} config.cancelButtonClass - Custom class for the cancel button.
     * @param {string} config.retryButtonClass - Custom class for the retry button.
     * @param {string|null} config.buttonType - Button type ('confirm', 'ok', 'retry', or null).
     * @param {boolean} config.showTitle - Whether to show the title.
     */
    createModal({
        type,
        title,
        content,
        confirmText,
        cancelText,
        customContentClass,
        customTitleClass,
        okButtonClass,
        confirmButtonClass,
        cancelButtonClass,
        retryButtonClass,
        buttonType,
        showTitle
    }) {
        const styles = this.getModalStyles(type);
        const modalId = `modal-${type}-${Date.now()}`;
        this.modal = document.createElement('div');
        this.modal.id = modalId;
        this.modal.tabIndex = -1;
        this.modal.className = 'hidden overflow-y-auto overflow-x-hidden fixed top-0 right-0 left-0 z-100000010 justify-center items-center w-full md:inset-0 h-[calc(100%-1rem)] max-h-full';
        this.modal.setAttribute('data-modal', 'true');

        let buttonsHtml = '';
        if (buttonType) {
            if (buttonType === 'confirm') {
                buttonsHtml = `
                    <button data-modal-confirm="${modalId}" type="button" class="${confirmButtonClass || styles.confirmButtonClass}">
                        ${confirmText || gettext('Yes, I\'m sure')}
                    </button>
                    <button data-modal-cancel="${modalId}" type="button" class="${cancelButtonClass || styles.cancelButtonClass}">
                        ${cancelText || gettext('No, cancel')}
                    </button>
                `;
            } else if (buttonType === 'ok') {
                buttonsHtml = `
                    <button data-modal-confirm="${modalId}" type="button" class="${okButtonClass || styles.buttonClass}">
                        ${confirmText || gettext('OK')}
                    </button>
                `;
            } else if (buttonType === 'retry') {
                buttonsHtml = `
                    <button data-modal-confirm="${modalId}" type="button" class="${retryButtonClass || styles.retryButtonClass}">
                        ${confirmText ? confirmText : `
                            <svg class="w-5 h-5 me-2" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24">
                                <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.651 7.65a7.131 7.131 0 0 0-12.68 3.15M18.001 4v4h-4m-7.652 8.35a7.13 7.13 0 0 0 12.68-3.15M6 20v-4h4"/>
                            </svg>
                            ${gettext('Retry')}
                        `}
                    </button>
                `;
            }
        }

        const titleHtml = showTitle ? `
            <h3 class="mb-5 text-lg font-normal text-gray-500 ${customTitleClass || ''}">${title || styles.title}</h3>
        ` : '';

        this.modal.innerHTML = `
            <div class="relative p-4 w-full max-w-md max-h-full">
                <div class="relative bg-white rounded-lg shadow-sm">
                    <button type="button" class="absolute top-3 end-2.5 text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 ms-auto inline-flex justify-center items-center" data-modal-hide="${modalId}">
                        <svg class="w-3 h-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 14 14">
                            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/>
                        </svg>
                        <span class="sr-only">${gettext('Close modal')}</span>
                    </button>
                    <div class="p-4 md:p-5 text-center">
                        ${styles.icon}
                        ${titleHtml}
                        <div class="text-lg ${customContentClass || ''}">${content || ''}</div>
                        <div class="mt-5 flex justify-center gap-3">
                            ${buttonsHtml}
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);
        this.modalInstance = new Modal(this.modal, {
            backdrop: 'dynamic',
            backdropClasses: 'bg-gray-900/50 fixed inset-0 z-100000009',
            closable: false,
            onHide: () => {
                if (!this.isClosing) {
                    this.isClosing = true;
                    if (this.resolveCallback) {
                        this.resolveCallback(false); // Resolve with `false` instead of rejecting on modal hide
                    }
                    this.closeModal();
                }
            }
        });
        this.initializeEventListeners(modalId);
    }

    /**
     * Initializes event listeners for modal buttons and backdrop.
     * @private
     * @param {string} modalId - The unique ID of the modal.
     */
    initializeEventListeners(modalId) {
        const confirmBtn = this.modal.querySelector(`[data-modal-confirm="${modalId}"]`);
        const cancelBtn = this.modal.querySelector(`[data-modal-cancel="${modalId}"]`);
        const closeBtn = this.modal.querySelector(`[data-modal-hide="${modalId}"]`);

        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                if (this.resolveCallback) {
                    this.resolveCallback(true); // Resolve with `true` on confirm
                    this.modalInstance.hide();
                }
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (this.resolveCallback) {
                    this.resolveCallback(false); // Resolve with `false` on cancel instead of rejecting
                    this.modalInstance.hide();
                }
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                if (this.resolveCallback) {
                    this.resolveCallback(false); // Resolve with `false` on close instead of rejecting
                    this.modalInstance.hide();
                }
            });
        }
    }

    /**
     * Closes the current modal and cleans up resources.
     * @example
     * sweetModalManager.closeModal();
     */
    closeModal() {
        if (this.modal && this.modalInstance && !this.isClosing) {
            this.isClosing = true;
            this.modal.remove();
            this.modal = null;
            this.modalInstance = null;
            this.resolveCallback = null;
            this.rejectCallback = null;
            this.isClosing = false;
        }
    }
}

/**
 * Builder class for configuring and displaying modals fluently.
 * @class
 */
class ModalBuilder {
    /**
     * @param {SweetModalManager} manager - The SweetModalManager instance.
     */
    constructor(manager) {
        this.manager = manager;
        this.config = {
            type: 'info',
            title: '',
            content: '',
            confirmText: '',
            cancelText: '',
            customContentClass: '',
            customTitleClass: '',
            okButtonClass: '',
            confirmButtonClass: '',
            cancelButtonClass: '',
            retryButtonClass: '',
            buttonType: null,
            showTitle: true
        };
    }

    /**
     * Sets the modal type.
     * @param {string} type - The modal type ('info', 'confirm', 'error', 'warning', 'success').
     * @returns {ModalBuilder} This builder instance.
     */
    setType(type) {
        this.config.type = type;
        return this;
    }

    /**
     * Sets a custom title for the modal.
     * @param {string} title - The custom title to display.
     * @returns {ModalBuilder} This builder instance.
     */
    setTitle(title) {
        this.config.title = title;
        return this;
    }

    /**
     * Sets the modal content (HTML or text).
     * @param {string} content - The content to display.
     * @returns {ModalBuilder} This builder instance.
     */
    setContent(content) {
        this.config.content = content;
        return this;
    }

    /**
     * Sets the confirm/retry button text.
     * @param {string} confirmText - The text for the confirm/retry button.
     * @returns {ModalBuilder} This builder instance.
     */
    setConfirmText(confirmText) {
        this.config.confirmText = confirmText;
        return this;
    }

    /**
     * Sets the cancel button text (for confirm modals).
     * @param {string} cancelText - The text for the cancel button.
     * @returns {ModalBuilder} This builder instance.
     */
    setCancelText(cancelText) {
        this.config.cancelText = cancelText;
        return this;
    }

    /**
     * Sets additional classes for the content div.
     * @param {string} customContentClass - The classes to add.
     * @returns {ModalBuilder} This builder instance.
     */
    setCustomContentClass(customContentClass) {
        this.config.customContentClass = customContentClass;
        return this;
    }

    /**
     * Sets additional classes for the title.
     * @param {string} customTitleClass - The classes to add.
     * @returns {ModalBuilder} This builder instance.
     */
    setCustomTitleClass(customTitleClass) {
        this.config.customTitleClass = customTitleClass;
        return this;
    }

    /**
     * Sets the custom class for the OK button.
     * @param {string} okButtonClass - The class for the OK button.
     * @returns {ModalBuilder} This builder instance.
     */
    setOkButtonClass(okButtonClass) {
        this.config.okButtonClass = okButtonClass;
        return this;
    }

    /**
     * Sets the custom class for the confirm button.
     * @param {string} confirmButtonClass - The class for the confirm button.
     * @returns {ModalBuilder} This builder instance.
     */
    setConfirmButtonClass(confirmButtonClass) {
        this.config.confirmButtonClass = confirmButtonClass;
        return this;
    }

    /**
     * Sets the custom class for the cancel button.
     * @param {string} cancelButtonClass - The class for the cancel button.
     * @returns {ModalBuilder} This builder instance.
     */
    setCancelButtonClass(cancelButtonClass) {
        this.config.cancelButtonClass = cancelButtonClass;
        return this;
    }

    /**
     * Sets the custom class for the retry button.
     * @param {string} retryButtonClass - The class for the retry button.
     * @returns {ModalBuilder} This builder instance.
     */
    setRetryButtonClass(retryButtonClass) {
        this.config.retryButtonClass = retryButtonClass;
        return this;
    }

    /**
     * Sets the button type to display.
     * @param {string|null} buttonType - The button type ('confirm', 'ok', 'retry', or null for no buttons).
     * @returns {ModalBuilder} This builder instance.
     */
    setButtonType(buttonType) {
        this.config.buttonType = buttonType;
        return this;
    }

    /**
     * Sets whether to show the modal title.
     * @param {boolean} showTitle - True to show the title, false to hide.
     * @returns {ModalBuilder} This builder instance.
     */
    setShowTitle(showTitle) {
        this.config.showTitle = showTitle;
        return this;
    }

    /**
     * Shows the configured modal and returns a Promise.
     * @returns {Promise<boolean>} Resolves with true on confirm/retry, false on cancel/close.
     * @example
     * sweetModalManager.buildModal()
     *     .setType('error')
     *     .setTitle('Network Error')
     *     .setContent('Failed to connect.')
     *     .setButtonType('retry')
     *     .setConfirmText('Try Again')
     *     .setShowTitle(true)
     *     .show()
     *     .then(result => console.log(result ? 'Retried' : 'Cancelled'));
     */
    show() {
        return new Promise((resolve, reject) => {
            this.manager.resolveCallback = resolve;
            this.manager.rejectCallback = reject;
            this.manager.createModal(this.config);
            this.manager.modalInstance.show();
        });
    }
}

// Export a singleton instance
const sweetModalManager = new SweetModalManager();
window.sweetModalManager = sweetModalManager;
