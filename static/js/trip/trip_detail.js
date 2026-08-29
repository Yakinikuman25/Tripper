document.addEventListener(
    "DOMContentLoaded",
    function () {

        // =================================
        // Trip旅行期間・旅行ルート
        // =================================

        const tripPeriodLine =
            document.getElementById(
                "trip-period-line"
            );

        const tripRouteLine =
            document.getElementById(
                "trip-route-line"
            );


        // =================================
        // Trip全体費用
        // =================================

        const tripExpenses =
            document.getElementById(
                "trip-expenses"
            );


        // =================================
        // 全体費用 費用名を必須化
        // =================================

        let tripExpenseNameInput =
            null;


        if (
            tripExpenses
            && tripExpenses.dataset.tripExpenseNameId
        ) {

            tripExpenseNameInput =
                document.getElementById(
                    tripExpenses.dataset.tripExpenseNameId
                );
        }


        if (tripExpenseNameInput) {

            tripExpenseNameInput.required =
                true;
        }


        // =================================
        // 全体費用 新規追加フォーム
        // =================================

        const showTripExpenseFormButton =
            document.getElementById(
                "show-trip-expense-form"
            );

        const hideTripExpenseFormButton =
            document.getElementById(
                "hide-trip-expense-form"
            );

        const tripExpenseAddForm =
            document.getElementById(
                "trip-expense-add-form"
            );


        if (
            showTripExpenseFormButton
            && tripExpenseAddForm
        ) {

            showTripExpenseFormButton.addEventListener(
                "click",
                function () {

                    showTripExpenseFormButton.style.display =
                        "none";

                    tripExpenseAddForm.style.display =
                        "block";
                }
            );
        }


        if (
            hideTripExpenseFormButton
            && showTripExpenseFormButton
            && tripExpenseAddForm
        ) {

            hideTripExpenseFormButton.addEventListener(
                "click",
                function () {

                    tripExpenseAddForm.style.display =
                        "none";

                    showTripExpenseFormButton.style.display =
                        "inline-block";
                }
            );
        }


        // =================================
        // 全体費用 編集フォーム
        // =================================

        document.addEventListener(
            "click",
            function (event) {

                const showEditButton =
                    event.target.closest(
                        ".show-trip-expense-edit"
                    );


                if (showEditButton) {

                    const expenseId =
                        showEditButton.dataset.expenseId;

                    const expenseDisplay =
                        document.getElementById(
                            `expense-display-${expenseId}`
                        );

                    const expenseEdit =
                        document.getElementById(
                            `expense-edit-${expenseId}`
                        );


                    if (
                        expenseDisplay
                        && expenseEdit
                    ) {

                        expenseDisplay.style.display =
                            "none";

                        expenseEdit.style.display =
                            "block";
                    }


                    return;
                }


                const hideEditButton =
                    event.target.closest(
                        ".hide-trip-expense-edit"
                    );


                if (hideEditButton) {

                    const expenseId =
                        hideEditButton.dataset.expenseId;

                    const expenseDisplay =
                        document.getElementById(
                            `expense-display-${expenseId}`
                        );

                    const expenseEdit =
                        document.getElementById(
                            `expense-edit-${expenseId}`
                        );


                    if (
                        expenseDisplay
                        && expenseEdit
                    ) {

                        expenseEdit.style.display =
                            "none";

                        expenseDisplay.style.display =
                            "block";
                    }
                }
            }
        );


        // =================================
        // 削除確認
        //
        // ・Trip全体費用
        // ・Day写真
        // ・Day感想
        // ・Day実際費用
        // ・Day費用明細
        //
        // data-confirm-message の内容を
        // 確認メッセージとして表示する
        // =================================

        document.addEventListener(
            "click",
            function (event) {

                const deleteButton =
                    event.target.closest(
                        ".confirm-trip-expense-delete, "
                        + ".confirm-day-record-delete"
                    );


                if (!deleteButton) {

                    return;
                }


                const message =
                    deleteButton.dataset.confirmMessage
                    || "削除しますか？";


                if (!window.confirm(message)) {

                    event.preventDefault();
                }
            }
        );


        // =================================
        // 全体費用 参考URL
        // =================================

        function setupExpenseReferenceUrlForms() {

            // -----------------------------
            // 「＋ 参考URL」
            // -----------------------------

            document.querySelectorAll(
                ".add-expense-reference-url"
            ).forEach(
                function (button) {

                    button.addEventListener(
                        "click",
                        function () {

                            const container =
                                document.getElementById(
                                    button.dataset.containerId
                                );

                            const template =
                                document.getElementById(
                                    button.dataset.templateId
                                );

                            const totalFormsInput =
                                document.getElementById(
                                    button.dataset.totalFormsId
                                );


                            if (
                                !container
                                || !template
                                || !totalFormsInput
                            ) {

                                return;
                            }


                            const formIndex =
                                parseInt(
                                    totalFormsInput.value,
                                    10
                                );


                            const newFormHtml =
                                template
                                    .innerHTML
                                    .replace(
                                        /__prefix__/g,
                                        formIndex
                                    );


                            container.insertAdjacentHTML(
                                "beforeend",
                                newFormHtml
                            );


                            totalFormsInput.value =
                                formIndex + 1;
                        }
                    );
                }
            );


            // -----------------------------
            // 参考URL 登録・削除
            // -----------------------------

            document.addEventListener(
                "click",
                function (event) {

                    const referenceUrlForm =
                        event.target.closest(
                            ".expense-reference-url-form"
                        );


                    if (!referenceUrlForm) {

                        return;
                    }


                    // -------------------------
                    // 登録
                    //
                    // このボタンは途中保存ではなく
                    // 入力確認用。
                    //
                    // DBへの最終保存は
                    // 全体費用の保存時に行う。
                    // -------------------------

                    if (
                        event.target.classList.contains(
                            "register-expense-reference-url"
                        )
                    ) {

                        const urlInput =
                            referenceUrlForm.querySelector(
                                'input[name$="-url"]'
                            );


                        if (
                            !urlInput
                            || !urlInput.value.trim()
                        ) {

                            alert(
                                "URLを入力してください。"
                            );

                            return;
                        }


                        event.target.textContent =
                            "登録済み";

                        return;
                    }


                    // -------------------------
                    // 削除
                    // -------------------------

                    if (
                        event.target.classList.contains(
                            "remove-expense-reference-url"
                        )
                    ) {

                        const deleteInput =
                            referenceUrlForm.querySelector(
                                'input[name$="-DELETE"]'
                            );


                        if (deleteInput) {

                            deleteInput.checked =
                                true;
                        }


                        referenceUrlForm.style.display =
                            "none";
                    }
                }
            );


            // -----------------------------
            // 登録後に内容を変更した場合
            // 「登録」に戻す
            // -----------------------------

            document.addEventListener(
                "input",
                function (event) {

                    if (
                        !event.target.matches(
                            '.expense-reference-url-form input[name$="-title"], '
                            + '.expense-reference-url-form input[name$="-url"]'
                        )
                    ) {

                        return;
                    }


                    const referenceUrlForm =
                        event.target.closest(
                            ".expense-reference-url-form"
                        );


                    if (!referenceUrlForm) {

                        return;
                    }


                    const registerButton =
                        referenceUrlForm.querySelector(
                            ".register-expense-reference-url"
                        );


                    if (
                        registerButton
                        && registerButton.textContent.trim()
                        === "登録済み"
                    ) {

                        registerButton.textContent =
                            "登録";
                    }
                }
            );
        }


        setupExpenseReferenceUrlForms();


        // =================================
        // Day費用明細 FormSet
        //
        // 「＋ 費用を追加」では保存せず、
        // 入力欄だけ増やす
        // =================================

        document.querySelectorAll(
            ".add-day-expense"
        ).forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const container =
                            document.getElementById(
                                button.dataset.containerId
                            );

                        const template =
                            document.getElementById(
                                button.dataset.templateId
                            );

                        const totalFormsInput =
                            document.getElementById(
                                button.dataset.totalFormsId
                            );


                        if (
                            !container
                            || !template
                            || !totalFormsInput
                        ) {

                            return;
                        }


                        const formIndex =
                            parseInt(
                                totalFormsInput.value,
                                10
                            );


                        const newFormHtml =
                            template
                                .innerHTML
                                .replace(
                                    /__prefix__/g,
                                    formIndex
                                );


                        container.insertAdjacentHTML(
                            "beforeend",
                            newFormHtml
                        );


                        totalFormsInput.value =
                            formIndex + 1;
                    }
                );
            }
        );


        // =================================
        // Day費用明細 FormSet内の削除
        //
        // ここではDBから削除しない。
        //
        // DELETEへチェックを付けて
        // フォームを非表示にし、
        // 最後の保存時に削除する。
        // =================================

        document.addEventListener(
            "click",
            function (event) {

                const removeButton =
                    event.target.closest(
                        ".remove-day-expense"
                    );


                if (!removeButton) {

                    return;
                }


                const expenseForm =
                    removeButton.closest(
                        ".day-expense-form"
                    );


                if (!expenseForm) {

                    return;
                }


                const deleteInput =
                    expenseForm.querySelector(
                        ".day-expense-delete-input"
                    );


                if (deleteInput) {

                    deleteInput.checked =
                        true;
                }


                expenseForm.style.display =
                    "none";
            }
        );


        // =================================
        // Trip旅行ルートの横幅調整
        // =================================

        if (
            tripPeriodLine
            && tripRouteLine
        ) {

            const periodWidth =
                tripPeriodLine
                    .getBoundingClientRect()
                    .width;


            /*
             * p要素は通常横幅いっぱいになるため、
             * 文字そのものの長さを測るために
             * 一時的なspanを作る
             */

            const measureSpan =
                document.createElement(
                    "span"
                );


            measureSpan.style.position =
                "absolute";

            measureSpan.style.visibility =
                "hidden";

            measureSpan.style.whiteSpace =
                "nowrap";

            measureSpan.style.font =
                window.getComputedStyle(
                    tripPeriodLine
                ).font;


            measureSpan.textContent =
                tripPeriodLine
                    .textContent
                    .replace(
                        /\s+/g,
                        " "
                    )
                    .trim();


            document.body.appendChild(
                measureSpan
            );


            const textWidth =
                measureSpan
                    .getBoundingClientRect()
                    .width;


            measureSpan.remove();


            tripRouteLine.style.maxWidth =
                Math.min(
                    textWidth,
                    periodWidth
                ) + "px";
        }
    }
);