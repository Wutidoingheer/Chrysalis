// Financial Analysis - Transaction-Level Debt Paydown Planner

let financialData = null;
let selectedCuts = {}; // { transactionIndex: cutAmount }

// File input handler
document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            financialData = JSON.parse(e.target.result);
            document.getElementById('fileStatus').textContent = `✅ Loaded ${file.name}`;
            document.getElementById('fileStatus').style.color = '#10b981';
            renderAnalysis();
        } catch (error) {
            document.getElementById('fileStatus').textContent = `❌ Error: ${error.message}`;
            document.getElementById('fileStatus').style.color = '#ef4444';
        }
    };
    reader.readAsText(file);
});

function renderAnalysis() {
    if (!financialData) return;
    
    document.getElementById('analysisContent').classList.remove('hidden');
    
    // Update summary cards
    const summary = financialData.summary;
    document.getElementById('ytdIncome').textContent = formatCurrency(summary.usaa_income_ytd);
    document.getElementById('ytdExpenses').textContent = formatCurrency(summary.usaa_expenses_ytd);
    document.getElementById('netFlow').textContent = formatCurrency(summary.usaa_net_flow_ytd);
    
    // Update header with analysis month
    const analysisMonth = financialData.metadata.analysis_month || financialData.metadata.previous_month;
    document.getElementById('transactionsHeader').textContent = `${analysisMonth} Transactions`;
    
    // Render debt cards
    renderDebtCards();
    
    // Render transactions
    renderTransactions();
    
    // Update impact preview
    updateImpactPreview();
}

function renderDebtCards() {
    const debtCardsContainer = document.getElementById('debtCards');
    debtCardsContainer.innerHTML = '';
    
    financialData.debts.forEach((debt, index) => {
        const card = document.createElement('div');
        card.className = 'debt-card';
        
        const monthlyInterest = (debt.balance * debt.apr / 100) / 12;
        const principalPayment = debt.payment - monthlyInterest;
        const monthsToPayoff = Math.ceil(debt.balance / principalPayment);
        const totalInterest = (monthsToPayoff * monthlyInterest) - (debt.balance - (monthsToPayoff * principalPayment));
        
        const progressPercent = Math.min(100, (debt.balance / (debt.balance + totalInterest)) * 100);
        
        card.innerHTML = `
            <h3>${debt.name}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <div style="font-size: 0.9em; color: #666;">Balance</div>
                    <div style="font-size: 1.5em; font-weight: bold; color: #333;">${formatCurrency(debt.balance)}</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: #666;">APR</div>
                    <div style="font-size: 1.5em; font-weight: bold; color: #333;">${debt.apr}%</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: #666;">Monthly Payment</div>
                    <div style="font-size: 1.5em; font-weight: bold; color: #333;">${formatCurrency(debt.payment)}</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: #666;">Months to Payoff</div>
                    <div style="font-size: 1.5em; font-weight: bold; color: #333;">${monthsToPayoff}</div>
                </div>
            </div>
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6; font-size: 0.9em; color: #666;">
                Total Interest: ${formatCurrency(totalInterest)}
            </div>
        `;
        
        debtCardsContainer.appendChild(card);
    });
}

function renderTransactions() {
    const tbody = document.getElementById('transactionsBody');
    tbody.innerHTML = '';
    
    const transactions = financialData.transactions.credit_cards_analysis_month || financialData.transactions.credit_cards_current_month;
    
    transactions.forEach((txn, index) => {
        const row = document.createElement('tr');
        row.className = 'transaction-row';
        row.dataset.index = index;
        
        const amount = parseFloat(txn.amount);
        const cutAmount = selectedCuts[index] || 0;
        const impact = calculateImpact(cutAmount);
        
        row.innerHTML = `
            <td>${formatDate(txn.posted_at)}</td>
            <td>${txn.account_name || 'N/A'}</td>
            <td>${txn.category || 'Uncategorized'}</td>
            <td>${txn.description_raw || 'N/A'}</td>
            <td class="amount ${amount < 0 ? 'negative' : 'positive'}">${formatCurrency(amount)}</td>
            <td>
                <input type="number" 
                       class="cut-amount" 
                       value="${cutAmount}" 
                       min="0" 
                       max="${Math.abs(amount)}"
                       step="0.01"
                       data-index="${index}"
                       placeholder="0.00">
            </td>
            <td class="impact">${formatImpact(impact)}</td>
        `;
        
        // Add event listeners
        const input = row.querySelector('.cut-amount');
        input.addEventListener('input', function() {
            const cutValue = parseFloat(this.value) || 0;
            selectedCuts[index] = cutValue;
            updateRowImpact(row, cutValue);
            updateImpactPreview();
        });
        
        row.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT') {
                this.classList.toggle('selected');
            }
        });
        
        tbody.appendChild(row);
    });
}

function updateRowImpact(row, cutAmount) {
    const impact = calculateImpact(cutAmount);
    const impactCell = row.querySelector('.impact');
    impactCell.innerHTML = formatImpact(impact);
}

function calculateImpact(cutAmount) {
    if (cutAmount <= 0) return null;
    
    // Calculate impact on each debt
    const impacts = financialData.debts.map(debt => {
        const monthlyInterest = (debt.balance * debt.apr / 100) / 12;
        const principalPayment = debt.payment - monthlyInterest;
        
        // If we add cutAmount to payment
        const newPayment = debt.payment + cutAmount;
        const newPrincipalPayment = newPayment - monthlyInterest;
        
        const oldMonths = Math.ceil(debt.balance / principalPayment);
        const newMonths = Math.ceil(debt.balance / newPrincipalPayment);
        const monthsSaved = oldMonths - newMonths;
        
        const oldTotalInterest = (oldMonths * monthlyInterest) - (debt.balance - (oldMonths * principalPayment));
        const newTotalInterest = (newMonths * monthlyInterest) - (debt.balance - (newMonths * newPrincipalPayment));
        const interestSaved = oldTotalInterest - newTotalInterest;
        
        return {
            debt: debt.name,
            monthsSaved,
            interestSaved,
            newMonths
        };
    });
    
    return impacts;
}

function formatImpact(impacts) {
    if (!impacts) return '-';
    
    // Show impact on highest APR debt (Avalanche method)
    const highestAPRDebt = financialData.debts.reduce((max, debt) => 
        debt.apr > max.apr ? debt : max
    );
    const impact = impacts.find(i => i.debt === highestAPRDebt.name);
    
    if (!impact || impact.monthsSaved <= 0) return '-';
    
    return `
        <div style="font-size: 0.85em;">
            <div style="color: #10b981;">${impact.monthsSaved} mo saved</div>
            <div style="color: #3b82f6;">$${formatNumber(impact.interestSaved)} interest saved</div>
        </div>
    `;
}

function updateImpactPreview() {
    const totalCut = Object.values(selectedCuts).reduce((sum, cut) => sum + (cut || 0), 0);
    
    if (totalCut <= 0) {
        document.getElementById('impactPreview').innerHTML = 
            '<p>Select transactions and enter cut amounts to see the impact on your debt paydown.</p>';
        return;
    }
    
    // Calculate aggregate impact
    const impacts = financialData.debts.map(debt => {
        const monthlyInterest = (debt.balance * debt.apr / 100) / 12;
        const principalPayment = debt.payment - monthlyInterest;
        
        const oldMonths = Math.ceil(debt.balance / principalPayment);
        const oldTotalInterest = (oldMonths * monthlyInterest) - (debt.balance - (oldMonths * principalPayment));
        
        const newPayment = debt.payment + totalCut;
        const newPrincipalPayment = newPayment - monthlyInterest;
        const newMonths = Math.ceil(debt.balance / newPrincipalPayment);
        const newTotalInterest = (newMonths * monthlyInterest) - (debt.balance - (newMonths * newPrincipalPayment));
        
        return {
            debt: debt.name,
            apr: debt.apr,
            monthsSaved: oldMonths - newMonths,
            interestSaved: oldTotalInterest - newTotalInterest,
            newMonths,
            newPayment
        };
    });
    
    // Sort by APR (Avalanche method)
    impacts.sort((a, b) => {
        const debtA = financialData.debts.find(d => d.name === a.debt);
        const debtB = financialData.debts.find(d => d.name === b.debt);
        return debtB.apr - debtA.apr;
    });
    
    let html = `
        <div style="margin-bottom: 20px;">
            <h4 style="color: #333; margin-bottom: 10px;">Total Monthly Cuts: ${formatCurrency(totalCut)}</h4>
            <p style="color: #666;">This is how much you can allocate to debt paydown each month.</p>
        </div>
    `;
    
    impacts.forEach(impact => {
        if (impact.monthsSaved > 0) {
            html += `
                <div class="impact-item">
                    <strong>${impact.debt} (${financialData.debts.find(d => d.name === impact.debt).apr}% APR)</strong>
                    <div style="margin-top: 8px;">
                        <div>💰 Interest Saved: <strong style="color: #10b981;">${formatCurrency(impact.interestSaved)}</strong></div>
                        <div>⏱️ Time Saved: <strong style="color: #3b82f6;">${impact.monthsSaved} months</strong></div>
                        <div>📅 New Payoff: <strong>${impact.newMonths} months</strong> (was ${impact.newMonths + impact.monthsSaved} months)</div>
                    </div>
                </div>
            `;
        }
    });
    
    // Show recommended allocation (Avalanche method)
    const highestAPR = impacts[0];
    html += `
        <div class="impact-item" style="background: #f8f9fa; border: 1px solid #dee2e6;">
            <strong>Recommended Strategy (Avalanche Method)</strong>
            <div style="margin-top: 8px;">
                <p>Put all ${formatCurrency(totalCut)}/month toward <strong>${highestAPR.debt}</strong> (highest APR at ${financialData.debts.find(d => d.name === highestAPR.debt).apr}%)</p>
                <p style="margin-top: 5px; font-size: 0.9em; color: #666;">
                    This will save you <strong>${formatCurrency(highestAPR.interestSaved)}</strong> in interest and pay it off <strong>${highestAPR.monthsSaved} months</strong> faster.
                </p>
            </div>
        </div>
    `;
    
    document.getElementById('impactPreview').innerHTML = html;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(num);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

