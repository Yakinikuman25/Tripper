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
        // Trip内容タブ
        //
        // 全体費用
        // 持ち物リスト
        // Day 1
        // Day 2
        // ...
        //
        // を横タブで切り替える
        // =================================

        const tripContentTabs =
            document.getElementById(
                "trip-content-tabs"
            );


        const tripContentTabsScroll =
            document.getElementById(
                "trip-content-tabs-scroll"
            );


        const tripTabsScrollLeft =
            document.getElementById(
                "trip-tabs-scroll-left"
            );


        const tripTabsScrollRight =
            document.getElementById(
                "trip-tabs-scroll-right"
            );


        const tripContentTabButtons =
            Array.from(
                document.querySelectorAll(
                    "[data-trip-content-tab]"
                )
            );


        const tripContentPanels =
            Array.from(
                document.querySelectorAll(
                    "[data-trip-content-panel]"
                )
            );



        // =================================
        // 指定されたタブを
        // 横スクロール領域内へ表示
        // =================================

        function scrollTabIntoView(
            button,
            behavior = "smooth"
        ) {

            if (
                !tripContentTabsScroll
                || !button
            ) {

                return;
            }


            const containerRect =
                tripContentTabsScroll
                    .getBoundingClientRect();


            const buttonRect =
                button
                    .getBoundingClientRect();


            // -----------------------------
            // 左側へ隠れている
            // -----------------------------

            if (
                buttonRect.left
                < containerRect.left
            ) {

                tripContentTabsScroll.scrollBy({
                    left:
                        buttonRect.left
                        - containerRect.left
                        - 8,

                    behavior: behavior,
                });


                return;
            }


            // -----------------------------
            // 右側へ隠れている
            // -----------------------------

            if (
                buttonRect.right
                > containerRect.right
            ) {

                tripContentTabsScroll.scrollBy({
                    left:
                        buttonRect.right
                        - containerRect.right
                        + 8,

                    behavior: behavior,
                });
            }

        }



        // =================================
        // 指定されたパネルを表示
        // =================================

        function activateTripContentPanel(
            targetId,
            options = {}
        ) {

            const {
                updateHash = false,
                scrollTab = true,
            } = options;


            if (
                !targetId
                || tripContentTabButtons.length === 0
                || tripContentPanels.length === 0
            ) {

                return;
            }


            const targetPanel =
                document.getElementById(
                    targetId
                );


            if (!targetPanel) {

                return;
            }



            // -----------------------------
            // パネル切り替え
            // -----------------------------

            tripContentPanels.forEach(
                function (panel) {

                    const isActive =
                        panel.id === targetId;


                    panel.hidden =
                        !isActive;

                }
            );



            // -----------------------------
            // タブボタン切り替え
            // -----------------------------

            let activeButton =
                null;


            tripContentTabButtons.forEach(
                function (button) {

                    const isActive =
                        button.dataset.target
                        === targetId;


                    button.classList.toggle(
                        "active",
                        isActive
                    );


                    button.setAttribute(
                        "aria-selected",
                        isActive
                            ? "true"
                            : "false"
                    );


                    button.tabIndex =
                        isActive
                            ? 0
                            : -1;


                    if (isActive) {

                        activeButton =
                            button;

                    }

                }
            );



            // -----------------------------
            // 選択したタブを
            // 横スクロール領域内へ表示
            // -----------------------------

            if (
                scrollTab
                && activeButton
            ) {

                scrollTabIntoView(
                    activeButton,
                    "smooth"
                );

            }



            // -----------------------------
            // URLのhash更新
            //
            // タブをクリック
            // ↓
            // #trip-expenses-panel
            // #trip-packing-panel
            // #day-panel-○○
            //
            // 再読み込みしても
            // 同じタブを開ける
            // -----------------------------

            if (updateHash) {

                const newUrl =
                    window.location.pathname
                    + window.location.search
                    + "#"
                    + targetId;


                window.history.replaceState(
                    null,
                    "",
                    newUrl
                );

            }

        }



        // =================================
        // URLのhashから
        // 開くべきパネルを取得
        //
        // 例
        //
        // #trip-expenses-panel
        // ↓
        // 全体費用
        //
        // #trip-packing-panel
        // ↓
        // 持ち物リスト
        //
        // #trip-packing-list
        // ↓
        // 持ち物リスト
        //
        // #packing-item-10
        // ↓
        // 持ち物リスト
        //
        // #day-panel-3
        // ↓
        // Day
        //
        // #trip-expense-3
        // ↓
        // 全体費用
        //
        // パネル内部の要素でも
        // 親パネルを開く
        // =================================

        function getPanelIdFromHash() {

            if (!window.location.hash) {

                return null;

            }


            let hashId;


            try {

                hashId =
                    decodeURIComponent(
                        window.location.hash.substring(
                            1
                        )
                    );

            } catch (error) {

                return null;

            }


            if (!hashId) {

                return null;

            }


            const hashElement =
                document.getElementById(
                    hashId
                );


            if (!hashElement) {

                return null;

            }



            // -----------------------------
            // hash先そのものがパネル
            // -----------------------------

            if (
                hashElement.matches(
                    "[data-trip-content-panel]"
                )
            ) {

                return hashElement.id;

            }



            // -----------------------------
            // hash先がパネル内部
            // -----------------------------

            const parentPanel =
                hashElement.closest(
                    "[data-trip-content-panel]"
                );


            if (parentPanel) {

                return parentPanel.id;

            }


            return null;

        }



        // =================================
        // 今日のDay取得
        //
        // HTML側で
        // data-is-today="true"
        // を付けたDayを探す
        // =================================

        function getTodayDayTarget() {

            const todayButton =
                tripContentTabButtons.find(
                    function (button) {

                        return (
                            button.dataset.isToday
                            === "true"
                        );

                    }
                );


            if (!todayButton) {

                return null;

            }


            return (
                todayButton.dataset.target
                || null
            );

        }



        // =================================
        // Day1取得
        // =================================

        function getFirstDayTarget() {

            const firstDayButton =
                tripContentTabButtons.find(
                    function (button) {

                        return (
                            button.dataset.dayId
                            !== undefined
                        );

                    }
                );


            if (!firstDayButton) {

                return null;

            }


            return (
                firstDayButton.dataset.target
                || null
            );

        }



        // =================================
        // 全体費用タブ取得
        // =================================

        function getTripExpenseTarget() {

            const expenseButton =
                tripContentTabButtons.find(
                    function (button) {

                        return (
                            button.dataset.tripExpenseTab
                            === "true"
                        );

                    }
                );


            if (!expenseButton) {

                return null;

            }


            return (
                expenseButton.dataset.target
                || null
            );

        }



        // =================================
        // 持ち物リストタブ取得
        // =================================

        function getTripPackingTarget() {

            const packingButton =
                tripContentTabButtons.find(
                    function (button) {

                        return (
                            button.dataset.target
                            === "trip-packing-panel"
                        );

                    }
                );


            if (!packingButton) {

                return null;

            }


            return (
                packingButton.dataset.target
                || null
            );

        }



        // =================================
        // 最初に存在するタブ取得
        //
        // 念のための最終フォールバック
        // =================================

        function getFirstAvailableTarget() {

            const firstButton =
                tripContentTabButtons[0];


            if (!firstButton) {

                return null;

            }


            return (
                firstButton.dataset.target
                || null
            );

        }



        // =================================
        // 初期表示するタブ
        //
        // 優先順位
        //
        // 1. URLのhash
        //
        //    持ち物追加・編集・削除・
        //    チェック後の
        //    #trip-packing-list
        //    もここで処理
        //
        // 2. traveling ＋ 今日のDay
        //
        // 3. Day1
        //
        // 4. 全体費用
        //
        // 5. 持ち物リスト
        //
        // 6. 最初に存在するタブ
        // =================================

        function setupInitialTripContentTab() {

            if (
                !tripContentTabs
                || tripContentTabButtons.length === 0
                || tripContentPanels.length === 0
            ) {

                return;

            }



            // -----------------------------
            // 1. URL hash
            // -----------------------------

            const hashTarget =
                getPanelIdFromHash();


            if (hashTarget) {

                activateTripContentPanel(
                    hashTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );


                return;

            }



            // -----------------------------
            // Trip状態
            // -----------------------------

            const tripStatus =
                tripContentTabs.dataset.tripStatus;



            // -----------------------------
            // 2. 旅中なら今日のDay
            // -----------------------------

            if (
                tripStatus === "traveling"
            ) {

                const todayTarget =
                    getTodayDayTarget();


                if (todayTarget) {

                    activateTripContentPanel(
                        todayTarget,
                        {
                            updateHash: false,
                            scrollTab: true,
                        }
                    );


                    return;

                }

            }



            // -----------------------------
            // 3. Day1
            // -----------------------------

            const firstDayTarget =
                getFirstDayTarget();


            if (firstDayTarget) {

                activateTripContentPanel(
                    firstDayTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );


                return;

            }



            // -----------------------------
            // 4. 全体費用
            // -----------------------------

            const expenseTarget =
                getTripExpenseTarget();


            if (expenseTarget) {

                activateTripContentPanel(
                    expenseTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );


                return;

            }



            // -----------------------------
            // 5. 持ち物リスト
            // -----------------------------

            const packingTarget =
                getTripPackingTarget();


            if (packingTarget) {

                activateTripContentPanel(
                    packingTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );


                return;

            }



            // -----------------------------
            // 6. 最初に存在するタブ
            // -----------------------------

            const firstAvailableTarget =
                getFirstAvailableTarget();


            if (firstAvailableTarget) {

                activateTripContentPanel(
                    firstAvailableTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );

            }

        }



        // =================================
        // タブクリック
        // =================================

        tripContentTabButtons.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const targetId =
                            button.dataset.target;


                        if (!targetId) {

                            return;

                        }


                        activateTripContentPanel(
                            targetId,
                            {
                                updateHash: true,
                                scrollTab: true,
                            }
                        );

                    }
                );

            }
        );



        // =================================
        // キーボード操作
        //
        // ← →
        //
        // 全体費用
        // 持ち物リスト
        // Day
        //
        // を順番に切り替え可能
        // =================================

        tripContentTabButtons.forEach(
            function (button) {

                button.addEventListener(
                    "keydown",
                    function (event) {

                        if (
                            event.key !== "ArrowLeft"
                            && event.key !== "ArrowRight"
                        ) {

                            return;

                        }


                        event.preventDefault();


                        const currentIndex =
                            tripContentTabButtons.indexOf(
                                button
                            );


                        if (currentIndex === -1) {

                            return;

                        }


                        let nextIndex;


                        if (
                            event.key === "ArrowRight"
                        ) {

                            nextIndex =
                                currentIndex + 1;


                            if (
                                nextIndex
                                >= tripContentTabButtons.length
                            ) {

                                nextIndex = 0;

                            }


                        } else {

                            nextIndex =
                                currentIndex - 1;


                            if (nextIndex < 0) {

                                nextIndex =
                                    tripContentTabButtons.length
                                    - 1;

                            }

                        }


                        const nextButton =
                            tripContentTabButtons[
                                nextIndex
                            ];


                        if (!nextButton) {

                            return;

                        }


                        const targetId =
                            nextButton.dataset.target;


                        if (!targetId) {

                            return;

                        }


                        activateTripContentPanel(
                            targetId,
                            {
                                updateHash: true,
                                scrollTab: true,
                            }
                        );


                        nextButton.focus();

                    }
                );

            }
        );



        // =================================
        // Trip内容タブ 横スクロール
        //
        // スワイプ・横スクロールに加えて
        // ‹ › ボタンでも移動できる
        // =================================

        if (
            tripContentTabsScroll
            && tripTabsScrollLeft
            && tripTabsScrollRight
        ) {


            // -----------------------------
            // 1回にスクロールする距離
            //
            // 基本的に
            // タブ1個分 + gap
            // -----------------------------

            function getTripTabScrollAmount() {

                const firstTab =
                    tripContentTabsScroll
                        .querySelector(
                            ".trip-content-tab-button"
                        );


                if (!firstTab) {

                    return 150;

                }


                const tabsStyle =
                    window.getComputedStyle(
                        tripContentTabsScroll
                    );


                const gap =
                    parseFloat(
                        tabsStyle.columnGap
                        || tabsStyle.gap
                    )
                    || 0;


                return (
                    firstTab.getBoundingClientRect().width
                    + gap
                );

            }



            // -----------------------------
            // 左へ
            // -----------------------------

            tripTabsScrollLeft.addEventListener(
                "click",
                function () {

                    tripContentTabsScroll.scrollBy({
                        left:
                            -getTripTabScrollAmount(),

                        behavior: "smooth",
                    });

                }
            );



            // -----------------------------
            // 右へ
            // -----------------------------

            tripTabsScrollRight.addEventListener(
                "click",
                function () {

                    tripContentTabsScroll.scrollBy({
                        left:
                            getTripTabScrollAmount(),

                        behavior: "smooth",
                    });

                }
            );



            // -----------------------------
            // 左右ボタンの
            // 有効・無効を更新
            // -----------------------------

            function updateTripTabScrollButtons() {

                const maxScrollLeft =
                    tripContentTabsScroll.scrollWidth
                    - tripContentTabsScroll.clientWidth;


                // 横スクロール自体が不要
                if (maxScrollLeft <= 1) {

                    tripTabsScrollLeft.disabled =
                        true;

                    tripTabsScrollRight.disabled =
                        true;


                    return;

                }


                // 左端
                tripTabsScrollLeft.disabled =
                    tripContentTabsScroll.scrollLeft
                    <= 1;


                // 右端
                tripTabsScrollRight.disabled =
                    tripContentTabsScroll.scrollLeft
                    >= maxScrollLeft - 1;

            }



            // -----------------------------
            // スクロール時
            // -----------------------------

            tripContentTabsScroll.addEventListener(
                "scroll",
                updateTripTabScrollButtons,
                {
                    passive: true,
                }
            );



            // -----------------------------
            // 画面サイズ変更時
            // -----------------------------

            window.addEventListener(
                "resize",
                updateTripTabScrollButtons
            );



            // -----------------------------
            // 初期状態
            // -----------------------------

            updateTripTabScrollButtons();


            // レイアウト確定後にも再確認
            window.requestAnimationFrame(
                function () {

                    updateTripTabScrollButtons();

                }
            );

        }



        // =================================
        // hashが変わった場合
        //
        // 全体費用
        // 持ち物リスト
        // Day
        //
        // の対応パネルを開く
        // =================================

        window.addEventListener(
            "hashchange",
            function () {

                const hashTarget =
                    getPanelIdFromHash();


                if (!hashTarget) {

                    return;

                }


                activateTripContentPanel(
                    hashTarget,
                    {
                        updateHash: false,
                        scrollTab: true,
                    }
                );

            }
        );



        // =================================
        // 初期タブ設定
        // =================================

        setupInitialTripContentTab();



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
        // ・Day自由実費
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


                        event.target.classList.remove(
                            "btn-primary"
                        );


                        event.target.classList.add(
                            "btn-outline-secondary"
                        );


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


                        registerButton.classList.remove(
                            "btn-outline-secondary"
                        );


                        registerButton.classList.add(
                            "btn-primary"
                        );

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