// === Thumbnail Preview Helpers (Global Scope for inline onchange) ===
window.previewSelectedThumbnail = function(input, previewId) {
    console.log("Previewing selected thumbnail for:", input.id, "to", previewId);
    const previewArea = document.getElementById(previewId);
    if (!previewArea) return;
    
    const previewImg = previewArea.querySelector('img');
    const label = document.querySelector(`label[for="${input.id}"]`);
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            if (previewImg) previewImg.src = e.target.result;
            previewArea.style.display = 'block';
            if (label) {
                label.innerHTML = '<i class="fa-solid fa-check"></i> تم الاختيار ✓';
                label.style.background = 'rgba(16, 185, 129, 0.2)';
                label.style.color = '#10b981';
                label.style.borderColor = '#10b981';
            }
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        previewArea.style.display = 'none';
        if (label) {
            label.innerHTML = '<i class="fa-solid fa-image"></i> صورة مصغرة';
            label.style.background = '';
            label.style.color = '';
            label.style.borderColor = '';
        }
    }
};

window.removeSelectedThumbnail = function(inputId, previewId) {
    const input = document.getElementById(inputId);
    const previewArea = document.getElementById(previewId);
    if (input) input.value = '';
    if (previewArea) previewArea.style.display = 'none';
    
    const label = document.querySelector(`label[for="${inputId}"]`);
    if (label) {
        label.innerHTML = '<i class="fa-solid fa-image"></i> صورة مصغرة';
        label.style.background = '';
        label.style.color = '';
        label.style.borderColor = '';
    }
};

document.addEventListener('DOMContentLoaded', async () => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  const originalFetch = window.fetch;
  window.fetch = async function () {
    let [resource, config] = arguments;
    if (config && (config.method === 'POST' || config.method === 'PUT' || config.method === 'DELETE')) {
      config.headers = config.headers || {};
      if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
    }
    return originalFetch.apply(this, arguments);
  };

  const urlParams = new URLSearchParams(window.location.search);
  const yErr = urlParams.get('youtube_error');
  if (yErr) {
    alert("مشكلة في ربط القناة: \n" + decodeURIComponent(yErr.replace(/\+/g, ' ')));
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  const yConn = urlParams.get('youtube_connected');
  if (yConn) {
    alert("تم ربط القناة بجيش المفاتيح بنجاح!");
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  const today = new Date().toISOString().slice(0, 10);

  // === State ===
  const mergeDateEl = document.getElementById('mergeDate');
  if (mergeDateEl) mergeDateEl.value = today;

  let statusTimeout = null;

  // === State Persistence ===
  function saveState(id) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.type === 'checkbox' || el.type === 'radio') {
      localStorage.setItem(`snapscrap_state_${id}`, el.checked);
    } else {
      localStorage.setItem(`snapscrap_state_${id}`, el.value);
    }
  }

  function loadState(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const val = localStorage.getItem(`snapscrap_state_${id}`);
    if (val !== null) {
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = (val === 'true');
      } else {
        el.value = val;
      }
    }
    // Attach listener for auto-save
    el.addEventListener('change', () => saveState(id));
  }

  // Restore States
  const persistentElements = [
    'batchMergeSidebar', 'mergeAfter', 'uploadPrivacy', 'uploadType',
    'uploadFilePrivacy', 'scheduleEnabled', 'scheduleHour', 'scheduleMinute', 'scheduleMerge'
  ];
  persistentElements.forEach(loadState);

  // === Modal Logic ===
  const modalBackdrop = document.getElementById('pipelineModal');
  const modalTitle = document.getElementById('pipelineModalTitle');
  const modalMessage = document.getElementById('pipelineModalMessage');
  const modalIcon = document.querySelector('.pipeline-status-icon i');
  const btnCancel = document.getElementById('btnPipelineCancel');
  const btnSkip = document.getElementById('btnPipelineSkipAccount');

  let currentModalTask = null;

  function showPipelineModal(taskId) {
      if(!modalBackdrop) return;
      currentModalTask = taskId;
      modalBackdrop.classList.add('visible');
      modalBackdrop.setAttribute('aria-hidden', 'false');
      
      const floating = document.getElementById('pipelineFloatingStatus');
      if (floating) floating.style.display = 'none';
      
      btnSkip.style.display = taskId.startsWith('batch_pipe_') ? 'inline-block' : 'none';
      btnCancel.disabled = false;
      btnCancel.innerHTML = '<i class="fa-solid fa-ban"></i> إلغاء العملية';
  }

  function hidePipelineModal() {
      if(!modalBackdrop) return;
      currentModalTask = null;
      modalBackdrop.classList.remove('visible');
      modalBackdrop.setAttribute('aria-hidden', 'true');
  }

  document.getElementById('pipelineModalMinimize')?.addEventListener('click', () => {
      hidePipelineModal();
      if (currentModalTask) {
          const floating = document.getElementById('pipelineFloatingStatus');
          if (floating) floating.style.display = 'block';
      }
  });

  document.getElementById('btnRestorePipeline')?.addEventListener('click', () => {
      if (currentModalTask) {
          showPipelineModal(currentModalTask);
          const floating = document.getElementById('pipelineFloatingStatus');
          if (floating) floating.style.display = 'none';
      }
  });

  btnCancel?.addEventListener('click', async () => {
      if (!currentModalTask) return;
      if (!confirm('هل أنت متأكد من رغبتك في إلغاء هذه العملية وإيقافها؟')) return;
      btnCancel.disabled = true;
      btnCancel.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري الإلغاء...';
      
      try {
          const res = await fetch(`/api/cancel_task/${currentModalTask}`, { method: 'POST' });
          const data = await res.json();
          if (data.ok) {
              modalMessage.textContent = 'تم إرسال طلب الإلغاء. بانتظار توقف المهام...';
          }
      } catch (e) {
          console.error(e);
      }
  });

  btnSkip?.addEventListener('click', async () => {
      if (!currentModalTask) return;
      btnSkip.disabled = true;
      setTimeout(() => { if(btnSkip) btnSkip.disabled = false; }, 3000); // prevent spam
      
      try {
          const res = await fetch(`/api/skip_task/${currentModalTask}`, { method: 'POST' });
          const data = await res.json();
          if (data.ok) {
              modalMessage.textContent = 'تم إرسال أمر تخطي الحساب الحالي...';
          }
      } catch (e) {
          console.error(e);
      }
  });

  function updateModal(type, msg, taskId) {
      if (!modalBackdrop.classList.contains('visible') && currentModalTask === taskId) {
          const floatingMsg = document.getElementById('floatingStatusMessage');
          if (floatingMsg) floatingMsg.textContent = msg || 'جاري تنفيذ العملية...';
          
          if (type === 'done' || type === 'error') {
              const floating = document.getElementById('pipelineFloatingStatus');
              if (floating) floating.style.display = 'none';
              showStatus(type, msg, false);
          }
          return;
      }

      if (modalBackdrop.classList.contains('visible') && currentModalTask === taskId) {
          modalMessage.textContent = msg || '';
          if (type === 'done') {
              modalTitle.textContent = 'اكتملت العملية بنجاح';
              modalIcon.className = 'fa-solid fa-check-circle';
              modalIcon.style.color = '#4ade80';
              btnCancel.style.display = 'none';
              btnSkip.style.display = 'none';
              setTimeout(hidePipelineModal, 5000); // Auto close after 5s
          } else if (type === 'error') {
              modalTitle.textContent = 'توقف بسبب خطأ';
              modalIcon.className = 'fa-solid fa-circle-exclamation';
              modalIcon.style.color = '#fca5a5';
              btnCancel.style.display = 'none';
              btnSkip.style.display = 'none';
              
              const floating = document.getElementById('pipelineFloatingStatus');
              if (floating) floating.style.display = 'none';
          } else if (type === 'queued') {
              modalTitle.textContent = 'العملية في طابور الانتظار...';
              modalIcon.className = 'fa-solid fa-hourglass-half fa-spin';
              modalIcon.style.color = '#fbbf24';
              btnCancel.style.display = 'inline-block';
              btnSkip.style.display = 'none';
          } else {
              modalTitle.textContent = 'جاري تنفيذ العملية...';
              modalIcon.className = 'fa-solid fa-circle-notch fa-spin';
              modalIcon.style.color = 'var(--snap-yellow)';
              btnCancel.style.display = 'inline-block';
          }
      }
  }

  // === Status ===
  async function pollTask(taskId, onDone) {
    const res = await fetch(`/api/task/${taskId}`);
    const data = await res.json();
    let type = (data.status === 'done' ? 'done' : 
                (data.status === 'error' || data.status === 'unknown') ? 'error' : 
                data.status === 'queued' ? 'queued' : 'running');

    let msg = data.message || '';
    if (data.status === 'unknown') msg = 'انقطع الاتصال بالمهمة (ربما بسبب تحديث الخادم). يرجى المحاولة مرة أخرى.';

    const isModalTask = taskId.startsWith('pl_') || taskId.startsWith('batch_pipe_');
    
    if (isModalTask && currentModalTask === taskId) {
        updateModal(type, msg, taskId);
    } else if (isModalTask && !currentModalTask && (type === 'running' || type === 'pending' || type === 'queued')) {
        // First time polling this modal task
        showPipelineModal(taskId);
        updateModal(type, msg, taskId);
    } else if (!isModalTask) {
        // Ensure toast is hidden for modal tasks explicitly, although if it's not a modal task we show normal status
        showStatus(type, msg);
    }

    if (data.status === 'pending' || data.status === 'running' || data.status === 'queued') {
      setTimeout(() => pollTask(taskId, onDone), 1000);
    } else if (data.status === 'done' && onDone) {
      if(isModalTask) {
         onDone();
      } else {
         onDone();
      }
    }
  }

  // === Task History Modal ===
  window.openHistoryModal = function() {
      const modal = document.getElementById('historyModal');
      if(modal) {
          modal.classList.add('visible');
          modal.setAttribute('aria-hidden', 'false');
          fetchTaskHistory();
      }
  };

  window.closeHistoryModal = function() {
      const modal = document.getElementById('historyModal');
      if(modal) {
          modal.classList.remove('visible');
          modal.setAttribute('aria-hidden', 'true');
      }
  };

  window.fetchTaskHistory = async function() {
      try {
          const res = await fetch('/api/task_history');
          const data = await res.json();
          const tbody = document.getElementById('historyTableBody');
          if(!tbody) return;
          
          if(!data.history || data.history.length === 0) {
              tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">لا توجد عمليات سابقة.</td></tr>';
              return;
          }
          
          tbody.innerHTML = '';
          const revHistory = [...data.history].reverse();
          
          revHistory.forEach(task => {
              const tr = document.createElement('tr');
              const d = new Date(task.timestamp);
              const dateStr = d.toLocaleString('ar-DZ', {hour12: true});
              
              let badgeClass = 'badge-running';
              let statusText = 'جاري';
              if(task.status === 'done') { badgeClass = 'badge-done'; statusText = 'مكتمل'; }
              else if(task.status === 'error') { badgeClass = 'badge-error'; statusText = 'خطأ/ملغى'; }
              else if(task.status === 'queued') { badgeClass = 'badge-queued'; statusText = 'انتظار'; }
              
              tr.innerHTML = `
                  <td>${dateStr}</td>
                  <td style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">${task.task_id}</td>
                  <td><span class="history-status-badge ${badgeClass}">${statusText}</span></td>
                  <td style="max-width:300px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${task.message}">${task.message}</td>
              `;
              tbody.appendChild(tr);
          });
          
      } catch(e) {
          console.error(e);
      }
  };

  function showStatus(type, msg, autoHide) {
    const section = document.getElementById('statusSection');
    const card = document.getElementById('statusCard');
    section.classList.add('visible');
    card.className = 'status-card ' + type;
    document.getElementById('statusTitle').textContent =
      type === 'done' ? 'تم بنجاح' : type === 'error' ? 'خطأ' : 'جاري المعالجة...';
    document.getElementById('statusMessage').textContent = msg || '';
    
    if (statusTimeout) clearTimeout(statusTimeout);
    
    // Persistent by default for 'done' and 'error' per user request
    if (type === 'done' || type === 'error') {
        if (autoHide === true) { // Only auto-hide if explicitly requested
           statusTimeout = setTimeout(() => section.classList.remove('visible'), 5000);
        }
    } else if (autoHide !== false) {
      // For 'running' or others, usually don't auto-hide unless specified
    }
  }

  const statusClose = document.getElementById('statusClose');
  if (statusClose) {
      statusClose.addEventListener('click', () => {
          document.getElementById('statusSection').classList.remove('visible');
      });
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    if (loading) btn.classList.add('loading'); else btn.classList.remove('loading');
  }

  // === Accounts ===
  async function addAccount(username) {
    const teamDropdown = document.getElementById('newAccountTeam');
    const team = teamDropdown ? teamDropdown.value : 'Other';

    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'add', username, team }),
    });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
      return;
    }
    renderAccounts(data.accounts);
    document.getElementById('newAccountInput').value = '';
    const bulkInput = document.getElementById('newAccounts');
    if (bulkInput) bulkInput.value = '';
    showStatus('done', `تم إضافة ${username}`);
  }

  async function removeAccount(username) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'remove', username }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  async function toggleAccount(username) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'toggle', username }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  function renderAccounts(accounts) {
    const list = document.getElementById('accountsList');
    if (!list) return;

    // Group accounts by team
    const groups = {};
    accounts.forEach(a => {
      const t = a.team || 'Other';
      if (!groups[t]) groups[t] = [];
      groups[t].push(a);
    });

    const teamOrder = ['Falcons', 'POWER', 'TU', 'PEAKS', 'LYNX', 'Twisted Minds', 'R8', 'Bitbot', 'Other'];
    const teamsConfig = window.TEAMS_CONFIG || {};

    let html = '';
    teamOrder.forEach(teamName => {
      const teamAccounts = groups[teamName];
      if (!teamAccounts || teamAccounts.length === 0) return;

      const teamHashtags = teamsConfig[teamName]?.hashtags || '';
      const allChecked = teamAccounts.every(a => a.checked);

      html += `
        <div class="team-group" data-team="${escapeHtml(teamName)}">
          <div class="team-header">
            <div class="team-header-title">
              <input type="checkbox" class="team-check" data-team="${escapeHtml(teamName)}" ${allChecked ? 'checked' : ''}>
              <span>${escapeHtml(teamName)}</span>
              <span style="font-size: 0.7rem; opacity: 0.6; font-weight: normal;">(${teamAccounts.length})</span>
            </div>
            <div class="team-actions">
               <!-- Future team actions here -->
            </div>
          </div>
          <input type="text" class="team-hashtags-input" data-team="${escapeHtml(teamName)}" 
                 placeholder="هاشتاقات موحدة لـ ${escapeHtml(teamName)}..." value="${escapeHtml(teamHashtags)}">
          
          <div class="team-members">
            ${teamAccounts.map(a => `
              <div class="account-item-wrapper" data-username="${escapeHtml(a.username)}">
                <div class="account-item-sidebar">
                  <input type="checkbox" class="account-check" data-username="${escapeHtml(a.username)}" ${a.checked ? 'checked' : ''}>
                  <div class="account-info" style="flex:1;">
                    <span class="account-name" title="${escapeHtml(a.username)}">${escapeHtml(a.username)}</span>
                  </div>
                  <button type="button" class="btn-remove-sm" data-username="${escapeHtml(a.username)}" title="حذف">×</button>
                </div>
                <div class="account-details-panel">
                  <div class="detail-field">
                    <label>الفريق:</label>
                    <select class="account-team-select" data-username="${escapeHtml(a.username)}" style="flex:1; background:rgba(255,255,255,0.05); border:1px dashed rgba(255,255,255,0.2); color:#fff; border-radius:4px; padding:2px 5px; font-size:0.75rem;">
                        ${teamOrder.map(t => `<option value="${t}" ${a.team === t || (!a.team && t === 'Other') ? 'selected' : ''}>${t === 'Other' ? 'بدون فريق' : t}</option>`).join('')}
                    </select>
                  </div>
                  <div class="detail-field">
                    <label>المؤثر:</label>
                    <input type="text" class="influencer-name-input" data-username="${escapeHtml(a.username)}" 
                           placeholder="اسم المؤثر..." value="${escapeHtml(a.influencer_name || '')}">
                  </div>
                  <div class="detail-field">
                    <label>هاشتاق:</label>
                    <input type="text" class="custom-hashtags-input" data-username="${escapeHtml(a.username)}" 
                           placeholder="#سناب #..." value="${escapeHtml(a.custom_hashtags || '')}">
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    });

    const emptyHtml = '<p class="empty-accounts" id="emptyAccounts" style="display:none">لا توجد حسابات</p>';
    list.innerHTML = html + emptyHtml;

    const emptyEl = document.getElementById('emptyAccounts');
    if (emptyEl) emptyEl.style.display = accounts.length ? 'none' : 'block';

    // EVENT LISTENERS
    
    // 1. Team-level logic
    list.querySelectorAll('.team-check').forEach(cb => {
      cb.addEventListener('change', async () => {
        const team = cb.dataset.team;
        const checked = cb.checked;
        const res = await fetch('/api/teams', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_team_checked', team, checked })
        });
        const data = await res.json();
        if (data.ok) renderAccounts(data.accounts);
      });
    });

    // 2. Team hashtags auto-save
    list.querySelectorAll('.team-hashtags-input').forEach(input => {
      input.addEventListener('blur', async () => {
        const team = input.dataset.team;
        const hashtags = input.value;
        await fetch('/api/teams', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_team_hashtags', team, hashtags })
        });
      });
    });

    // 3. Account-level metadata auto-save (Influencer, Hashtags, Team)
    list.querySelectorAll('.influencer-name-input').forEach(input => {
      input.addEventListener('blur', async () => {
        const username = input.dataset.username;
        const name = input.value;
        await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_influencer', username, influencer_name: name })
        });
      });
    });

    list.querySelectorAll('.custom-hashtags-input').forEach(input => {
      input.addEventListener('blur', async () => {
        const username = input.dataset.username;
        const hashtags = input.value;
        await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_hashtags', username, custom_hashtags: hashtags })
        });
      });
    });

    list.querySelectorAll('.account-team-select').forEach(select => {
      select.addEventListener('change', async () => {
        const username = select.dataset.username;
        const team = select.value;
        const res = await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_team', username, team })
        });
        const data = await res.json();
        if (data.ok) renderAccounts(data.accounts);
      });
    });

    let teamHashtagTimer;
    list.querySelectorAll('.team-hashtags-input').forEach(input => {
      input.addEventListener('input', () => {
        clearTimeout(teamHashtagTimer);
        const team = input.dataset.team;
        teamHashtagTimer = setTimeout(() => {
          fetch('/api/teams', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_team_hashtags', team, hashtags: input.value })
          });
          // Update local cache
          if (!window.TEAMS_CONFIG) window.TEAMS_CONFIG = {};
          if (!window.TEAMS_CONFIG[team]) window.TEAMS_CONFIG[team] = {};
          window.TEAMS_CONFIG[team].hashtags = input.value;
        }, 1000);
      });
    });

    // 2. Account-level logic
    list.querySelectorAll('.account-team-select').forEach(sel => {
      sel.addEventListener('change', async (e) => {
        const username = e.target.dataset.username;
        const newTeam = e.target.value;
        const res = await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'set_team', username, team: newTeam })
        });
        const data = await res.json();
        if (data.ok) renderAccounts(data.accounts);
      });
    });

    list.querySelectorAll('.account-check').forEach(cb => {
      cb.addEventListener('change', () => toggleAccount(cb.dataset.username));
    });
    
    list.querySelectorAll('.btn-remove-sm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault(); e.stopPropagation();
        removeAccount(btn.dataset.username);
      });
    });

    let debInfluencer;
    list.querySelectorAll('.influencer-name-input').forEach(input => {
      input.addEventListener('input', () => {
        clearTimeout(debInfluencer);
        debInfluencer = setTimeout(() => {
          fetch('/api/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_influencer', username: input.dataset.username, influencer_name: input.value })
          });
        }, 800);
      });
    });

    let debHashtags;
    list.querySelectorAll('.custom-hashtags-input').forEach(input => {
      input.addEventListener('input', () => {
        clearTimeout(debHashtags);
        debHashtags = setTimeout(() => {
          fetch('/api/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_hashtags', username: input.dataset.username, custom_hashtags: input.value })
          });
        }, 800);
      });
    });

    // Sync pipeline dropdown
    const pipelineSel = document.getElementById('pipelineUsername');
    if (pipelineSel) {
      const cur = pipelineSel.value;
      pipelineSel.innerHTML = '<option value="">اختر المستخدم (من جيش سناب)</option>' +
        accounts.map(a => `<option value="${escapeHtml(a.username)}">${escapeHtml(a.username)} ${a.influencer_name ? '(' + escapeHtml(a.influencer_name) + ')' : ''}</option>`).join('');
      if (cur && accounts.some(a => a.username === cur)) pipelineSel.value = cur;
    }
  }

  async function setAllChecked(checked) {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'set_all_checked', checked }),
    });
    const data = await res.json();
    if (data.ok) renderAccounts(data.accounts);
  }

  document.getElementById('selectAll')?.addEventListener('click', () => setAllChecked(true));
  document.getElementById('deselectAll')?.addEventListener('click', () => setAllChecked(false));

  document.getElementById('btnSetupBot')?.addEventListener('click', async () => {
    try {
        const btn = document.getElementById('btnSetupBot');
        btn.disabled = true;
        btn.innerHTML = 'جاري التشغيل...';
        const res = await fetch('/api/run-setup-bot', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert('تم تشغيل أداة إعداد الروبوت! الرجاء النظر إلى شاشة الحاسوب لتسجيل الدخول.');
        } else {
            alert('حدث خطأ: ' + data.error);
        }
    } catch (e) {
        alert('حدث خطأ بالاتصال.');
    } finally {
        const btn = document.getElementById('btnSetupBot');
        if(btn) {
            btn.disabled = false;
            btn.innerHTML = '🤖 إعداد روبوت يوتيوب';
        }
    }
  });

  // Toggle Bulk Add (Reverted to Toggle Link)
  const toggleBulkLink = document.getElementById('toggleBulkAdd');
  const singleInput = document.getElementById('newAccountInput');
  const bulkInput = document.getElementById('newAccounts');
  const addBtn = document.querySelector('#addAccountForm button[type="submit"]');

  if (toggleBulkLink) {
    toggleBulkLink.addEventListener('click', () => {
      if (bulkInput.style.display === 'none') {
        bulkInput.style.display = 'block';
        singleInput.parentElement.style.display = 'none'; // Hide input-row
        if (addBtn) addBtn.textContent = 'إضافة دفعة';
      } else {
        bulkInput.style.display = 'none';
        singleInput.parentElement.style.display = 'flex';
        if (addBtn) addBtn.textContent = 'إضافة';
      }
    });
  }

  // === Suggested accounts ===
  async function loadSuggestedAccounts() {
    const list = document.getElementById('suggestedList');
    if (!list) return;
    try {
      const res = await fetch('/api/suggested-accounts');
      const data = await res.json();
      const accounts = data.accounts || [];
      list.innerHTML = accounts.map(a => `
        <label class="suggested-item">
          <input type="checkbox" class="suggested-check" data-username="${escapeHtml(a.username)}">
          <span>${escapeHtml(a.label || a.username)}</span>
        </label>
      `).join('');
    } catch {
      list.innerHTML = '<span class="empty-accounts">فشل تحميل الحسابات المقترحة</span>';
    }
  }

  // Toggle Suggestions
  const suggestedHeader = document.getElementById('suggestedHeader');
  const suggestedList = document.getElementById('suggestedList');
  const toggleIcon = document.getElementById('suggestedToggleIcon');

  if (suggestedHeader && suggestedList) {
    suggestedHeader.addEventListener('click', (e) => {
      // Prevent toggle if clicking the refresh button
      if (e.target.closest('#refreshSuggested')) return;

      if (suggestedList.style.display === 'none') {
        suggestedList.style.display = 'flex'; // Changed to flex to match CSS
        suggestedHeader.classList.remove('collapsed');
        if (toggleIcon) toggleIcon.style.transform = 'rotate(0deg)';
      } else {
        suggestedList.style.display = 'none';
        suggestedHeader.classList.add('collapsed');
        if (toggleIcon) toggleIcon.style.transform = 'rotate(90deg)';
      }
    });
  }

  loadSuggestedAccounts();

  document.getElementById('refreshSuggested')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshSuggested');
    btn.disabled = true;
    btn.classList.add('loading'); // Use CSS spinner if available or just wait
    await loadSuggestedAccounts();
    btn.disabled = false;
    btn.classList.remove('loading');
    showStatus('done', 'تم تحديث الحسابات المقترحة');
  });

  document.getElementById('addSelectedSuggested')?.addEventListener('click', async () => {
    const checked = [...document.querySelectorAll('.suggested-check:checked')].map(cb => cb.dataset.username);
    if (!checked.length) {
      showStatus('error', 'حدّد حسابات لإضافتها');
      return;
    }
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'add_bulk', usernames: checked }),
    });
    const data = await res.json();
    if (data.ok) {
      renderAccounts(data.accounts);
      const msg = data.added > 0 ? `تم إضافة ${data.added} حساب${data.added > 1 ? 'ات' : ''}` : 'كل المحدد موجود مسبقاً';
      showStatus('done', msg);
      document.querySelectorAll('.suggested-check:checked').forEach(cb => { cb.checked = false; });
    } else {
      showStatus('error', data.error || 'خطأ');
    }
  });

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // Add Account Form Submit
  document.getElementById('addAccountForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const isBulk = bulkInput && bulkInput.style.display !== 'none';
    let usernames = [];

    if (isBulk) {
      const text = bulkInput.value;
      usernames = text.split(/\r?\n|,/).map(s => s.trim().toLowerCase()).filter(Boolean);
    } else {
      const val = singleInput.value.trim().toLowerCase();
      if (val) usernames = [val];
    }

    if (!usernames.length) {
      showStatus('error', 'أدخل اسم مستخدم');
      return;
    }

    const btn = document.getElementById('submitAddBtn') || addBtn;
    setLoading(btn, true);

    try {
      if (usernames.length === 1) {
        await addAccount(usernames[0]);
      } else {
        const teamDropdown = document.getElementById('newAccountTeam');
        const team = teamDropdown ? teamDropdown.value : 'Other';
        const res = await fetch('/api/accounts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'add_bulk', usernames, team }),
        });
        const data = await res.json();
        if (!data.ok) {
          showStatus('error', data.error);
        } else {
          renderAccounts(data.accounts);

          // Clear inputs
          if (bulkInput) bulkInput.value = '';
          if (document.getElementById('newAccountInput')) document.getElementById('newAccountInput').value = '';

          const msg = data.added > 0 ? `تم إضافة ${data.added} حساب` : '';
          const skip = data.skipped?.length ? ` (${data.skipped.length} موجود)` : '';
          showStatus('done', msg + skip || 'تم');
        }
      }
    } catch (err) {
      showStatus('error', 'حدث خطأ غير متوقع');
    } finally {
      setLoading(btn, false);
    }
  });

  document.getElementById('downloadSelected')?.addEventListener('click', async () => {
    const checked = [...document.querySelectorAll('.account-check:checked')].map(cb => cb.dataset.username);
    if (!checked.length) {
      showStatus('error', 'حدّد حسابات لتنزيلها');
      return;
    }
    const btn = document.getElementById('downloadSelected');
    setLoading(btn, true);
    // Use the sidebar checkbox
    const merge = document.getElementById('batchMergeSidebar')?.checked || false;
    const res = await fetch('/api/download-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usernames: checked, merge }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري التحميل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  renderAccounts(window.INIT_ACCOUNTS || []);

  // === Refresh merged folders ===
  async function refreshMergedFolders() {
    const res = await fetch('/api/merged-folders');
    const folders = await res.json();

    // Upload folder select
    const sel = document.getElementById('uploadUsername');
    if (sel) {
      const currentVal = sel.value;
      const opts = '<option value="">اختر المجلد</option><option value="__manual__">أدخل يدوياً</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
      sel.innerHTML = opts;
      if (currentVal) sel.value = currentVal;
    }

    // Clear folder select
    const clearSel = document.getElementById('clearFolder');
    if (clearSel) {
      clearSel.innerHTML = '<option value="">اختر المجلد</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
    }

    // TikTok folder select
    const tiktokSel = document.getElementById('tiktokFolder');
    if (tiktokSel) {
      tiktokSel.innerHTML = '<option value="">اختر المجلد</option>' +
        folders.map(f => `<option value="${escapeHtml(f.username)}" data-date="${escapeHtml(f.date)}">${escapeHtml(f.username)} / ${escapeHtml(f.date)}</option>`).join('');
    }
  }

  document.getElementById('refreshMerged')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshMerged');
    btn.disabled = true;
    btn.textContent = '...';
    await refreshMergedFolders();
    // await refreshClearFolders(); // Handled by refreshMergedFolders now
    btn.disabled = false;
    btn.textContent = '↻ مجلدات';
    showStatus('done', 'تم تحديث قائمة المجلدات');
  });

  // === Schedule + next run ===
  function updateNextRun() {
    const el = document.getElementById('nextRun');
    if (!el) return;
    const enabled = document.getElementById('scheduleEnabled')?.checked;
    if (!enabled) {
      el.textContent = '';
      return;
    }
    const h = parseInt(document.getElementById('scheduleHour')?.value) || 9;
    const m = parseInt(document.getElementById('scheduleMinute')?.value) || 0;
    const now = new Date();
    let next = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
    if (next <= now) next.setDate(next.getDate() + 1);
    const opts = { hour: '2-digit', minute: '2-digit', weekday: 'short' };
    el.textContent = 'التشغيل التالي: ' + next.toLocaleDateString('ar-SA', opts);
  }

  document.getElementById('scheduleEnabled')?.addEventListener('change', updateNextRun);
  document.getElementById('scheduleHour')?.addEventListener('change', updateNextRun);
  document.getElementById('scheduleMinute')?.addEventListener('change', updateNextRun);
  setTimeout(updateNextRun, 100);

  // === Schedule ===
  document.getElementById('scheduleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: document.getElementById('scheduleEnabled').checked,
        hour: parseInt(document.getElementById('scheduleHour').value) || 9,
        minute: parseInt(document.getElementById('scheduleMinute').value) || 0,
        merge: document.getElementById('scheduleMerge').checked,
      }),
    });
    const data = await res.json();
    setLoading(btn, false);
    if (data.ok) {
      showStatus('done', 'تم حفظ الجدولة');
      updateNextRun();
    }
  });

  // === Mini Tabs (Upload Folder/File) ===
  const uploadTabs = document.querySelectorAll('.upload-card .tab');
  const uploadContents = document.querySelectorAll('.upload-card .tab-content');

  function switchUploadMiniTab(tabName) {
    uploadTabs.forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
    });
    uploadContents.forEach(c => {
      const isActive = (c.id === (tabName === 'folder' ? 'uploadFolder' : 'uploadFile'));
      c.classList.toggle('active', isActive);
    });
    localStorage.setItem('snapscrap_active_upload_tab', tabName);
  }

  uploadTabs.forEach(tab => {
    tab.addEventListener('click', () => switchUploadMiniTab(tab.dataset.tab));
  });

  // Restore mini-tab
  const savedUploadTab = localStorage.getItem('snapscrap_active_upload_tab');
  if (savedUploadTab) switchUploadMiniTab(savedUploadTab);

  // === Upload select ===
  const uploadUsername = document.getElementById('uploadUsername');
  const uploadDate = document.getElementById('uploadDate');
  const manualUpload = document.getElementById('manualUpload');
  uploadUsername?.addEventListener('change', () => {
    const opt = uploadUsername.options[uploadUsername.selectedIndex];
    const val = opt?.value || '';
    if (val === '__manual__') {
      manualUpload.style.display = 'flex';
      uploadDate.value = '';
    } else {
      manualUpload.style.display = 'none';
      uploadDate.value = opt?.dataset?.date || '';
    }
  });

  // === File drop ===
  const fileDrop = document.getElementById('fileDrop');
  const videoFile = document.getElementById('videoFile');
  const fileSelectedEl = document.getElementById('fileSelected');
  function updateFileSelected() {
    const f = videoFile?.files[0];
    if (fileSelectedEl) {
      fileSelectedEl.style.display = f ? 'block' : 'none';
      fileSelectedEl.textContent = f ? '✓ ' + f.name : '';
    }
  }
  videoFile?.addEventListener('change', updateFileSelected);
  fileDrop?.addEventListener('click', () => videoFile?.click());
  fileDrop?.addEventListener('dragover', (e) => { e.preventDefault(); fileDrop.classList.add('dragover'); });
  fileDrop?.addEventListener('dragleave', () => fileDrop.classList.remove('dragover'));
  fileDrop?.addEventListener('drop', (e) => {
    e.preventDefault();
    fileDrop.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      videoFile.files = e.dataTransfer.files;
      updateFileSelected();
    }
  });

  // === Download ===
  document.getElementById('downloadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const merge = document.getElementById('mergeAfter')?.checked || false;
    const todayOnly = document.getElementById('dlTodayOnly')?.checked || false;
    const customLinks = document.getElementById('dlCustomLinks')?.value.trim() || "";
    if (!username) {
      showStatus('error', 'أدخل اسم المستخدم');
      return;
    }
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, merge, today_only: todayOnly, custom_links: customLinks }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري التحميل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === YouTube channels ===
  function populateChannelSelects(channels) {
    const opts = '<option value="">اختر القناة</option>' +
      (channels || []).map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.title)}</option>`).join('');
    const sel1 = document.getElementById('uploadChannel');
    const sel2 = document.getElementById('uploadFileChannel');
    const sel3 = document.getElementById('bulkUploadChannel');
    const sel4 = document.getElementById('pipelineChannel');
    const sel5 = document.getElementById('batchPipeChannel');

    [sel1, sel2, sel3, sel4, sel5].forEach(sel => {
      if (sel) {
        const v = sel.value;
        sel.innerHTML = opts;
        if (v) sel.value = v;

        if (sel.id === 'bulkUploadChannel' && !v && channels) {
          const targetChannel = channels.find(c => c.title.toLowerCase().includes("content creators stories") || c.title.toLowerCase().includes("stories"));
          if (targetChannel) {
            sel.value = targetChannel.id;
          }
        }

        // Restore from storage if empty
        if (!v) {
          const stored = localStorage.getItem(`snapscrap_state_${sel.id}`);
          if (stored) sel.value = stored;
        }
        sel.addEventListener('change', () => saveState(sel.id));
      }
    });
  }

  async function loadYoutubeChannels() {
    const el = document.getElementById('youtubeChannels');
    try {
      const res = await fetch('/api/youtube/channels');
      const data = await res.json();
      if (data.ok && data.channels?.length) {
        populateChannelSelects(data.channels);
        if (el) el.textContent = 'قناتك: ' + data.channels.map(c => c.title).join('، ');
      } else {
        populateChannelSelects([]);
        if (el) el.textContent = data.error || 'أضف قناة عبر «+ إضافة قناة»';
      }
    } catch {
      populateChannelSelects([]);
      if (el) el.textContent = '';
    }
  }
  loadYoutubeChannels();

  document.getElementById('refreshChannels')?.addEventListener('click', async () => {
    const btn = document.getElementById('refreshChannels');
    btn.disabled = true;
    btn.textContent = '...';
    const res = await fetch('/api/youtube/refresh', { method: 'POST' });
    const data = await res.json();
    btn.disabled = false;
    btn.textContent = '↻ قنوات';
    if (data.ok) {
      populateChannelSelects(data.channels);
      showStatus('done', 'تم تحديث القنوات');
    } else {
      showStatus('error', data.error || 'فشل التحديث');
    }
  });

  // URL params: youtube_connected, youtube_error
  const params = new URLSearchParams(location.search);
  if (params.get('youtube_connected')) {
    loadYoutubeChannels();
    showStatus('done', 'تم إضافة القناة بنجاح');
    history.replaceState({}, '', location.pathname);
  }
  if (params.get('youtube_error')) {
    showStatus('error', decodeURIComponent(params.get('youtube_error') || 'خطأ'));
    history.replaceState({}, '', location.pathname);
  }

  // === Merge ===
  document.getElementById('mergeForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('mergeUsername').value.trim();
    const date = (document.getElementById('mergeDate').value || today).trim();
    const mergeMode = document.querySelector('input[name="mergeMode"]:checked')?.value || 'shorts';
    if (!username) {
      showStatus('error', 'أدخل اسم المستخدم');
      return;
    }
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    const res = await fetch('/api/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date, merge_mode: mergeMode }),
    });
    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري الدمج...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === Upload folder ===
  async function handleUpload(isLong) {
    const uploadUsernameSel = document.getElementById('uploadUsername');
    const sel = uploadUsernameSel.value;
    const isManual = sel === '__manual__';
    const username = isManual
      ? document.getElementById('uploadUsernameManual')?.value?.trim()
      : sel.trim();

    const selectedOption = uploadUsernameSel.options[uploadUsernameSel.selectedIndex];
    const optionDate = selectedOption ? selectedOption.getAttribute('data-date') : '';

    const date = (isManual
      ? document.getElementById('uploadDateManual')?.value?.trim()
      : optionDate?.trim()) || today;

    const privacy = document.getElementById('uploadPrivacy')?.value || 'private';
    const uploadType = isLong ? 'long' : 'shorts';
    const channelId = document.getElementById('uploadChannel')?.value || null;
    const customTitle = document.getElementById('uploadCustomTitle')?.value?.trim() || null;

    if (!username) {
      showStatus('error', 'اختر مجلداً أو أدخل اسم المستخدم');
      return;
    }

    try {
      // Upload thumbnail if provided
      let customThumbPath = null;
      const thumbInput = document.getElementById('uploadCustomThumb');
      if (thumbInput && thumbInput.files && thumbInput.files.length > 0) {
        showStatus('running', 'جاري رفع الصورة المصغرة...');
        customThumbPath = await uploadTempThumb('uploadCustomThumb');
      }

      const res = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          username, 
          date, 
          privacy, 
          upload_type: uploadType, 
          channel_id: channelId || undefined,
          custom_long_title: customTitle,
          custom_thumb_path: customThumbPath
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        showStatus('error', data.error);
        return;
      }
      showStatus('running', 'جاري الرفع إلى يوتيوب...');
      pollTask(data.task_id);
    } catch (err) {
      console.error(err);
      showStatus('error', 'انتهت الجلسة (CSRF) أو فشل الاتصال بالخادم. يرجى تحديث الصفحة وحاول مجدداً.');
    }
  }

  document.getElementById('uploadForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    handleUpload(false);
  });
  document.getElementById('btnUploadLong')?.addEventListener('click', () => {
    handleUpload(true);
  });

  // === Upload file ===
  document.getElementById('uploadFileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = videoFile.files[0];
    if (!file) {
      showStatus('error', 'اختر ملف فيديو');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', document.getElementById('uploadTitle')?.value?.trim() || file.name.replace(/\.[^.]+$/, ''));
    formData.append('privacy', document.getElementById('uploadFilePrivacy')?.value || 'private');
    
    const thumbFile = document.getElementById('uploadFileThumb')?.files[0];
    if (thumbFile) {
      formData.append('thumbnail', thumbFile);
    }

    const channelId = document.getElementById('uploadFileChannel')?.value;
    if (channelId) formData.append('channel_id', channelId);
    const res = await fetch('/api/upload-file', { method: 'POST', body: formData });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
      return;
    }
    showStatus('running', 'جاري الرفع إلى يوتيوب...');
    pollTask(data.task_id);
  });

  async function uploadTempThumb(inputId) {
    const input = document.getElementById(inputId);
    if (!input || !input.files || !input.files[0]) return null;
    const formData = new FormData();
    formData.append('thumb_file', input.files[0]);
    try {
      const res = await fetch('/api/upload-temp-thumb', { method: 'POST', body: formData });
      const data = await res.json();
      return data.ok ? data.path : null;
    } catch { return null; }
  }

  // === Pipeline ===
  async function handlePipeline(uploadType, btn) {
    const pipelineUserEl = document.getElementById('pipelineUsername');
    const username = pipelineUserEl ? pipelineUserEl.value.trim() : '';
    const date = document.getElementById('pipelineDate')?.value?.trim() || today;
    const privacy = 'public'; // Force public as per user's usual preference or extract from UI if needed
    const channelId = document.getElementById('pipelineChannel')?.value || null;
    const publishAt = document.getElementById('pipelinePublishAt')?.value || null;
    const force = document.getElementById('pipelineForce')?.checked || false;
    const skipFirstInput = document.getElementById('pipelineSkipFirst');
    const skipFirst = skipFirstInput ? parseInt(skipFirstInput.value) || 0 : 0;

    const todayOnly = document.getElementById('pipelineTodayOnly')?.checked || false;
    const customLinks = document.getElementById('pipelineCustomLinks')?.value.trim() || "";

    const customTitleInput = document.getElementById('pipelineCustomTitle');
    const customLongTitle = customTitleInput ? customTitleInput.value.trim() : null;

    if (!username) {
      showStatus('error', 'اختر المستخدم أولاً');
      return;
    }
    // If NOT prepare mode, we MUST have a channelId
    if (uploadType !== 'prepare' && !channelId) {
      showStatus('error', 'اختر القناة أولاً');
      return;
    }

    setLoading(btn, true);
    
    // Upload thumbnail if provided
    let customThumbPath = null;
    if (document.getElementById('pipelineCustomThumb')?.files?.length > 0) {
      showStatus('running', 'جاري رفع الصورة المصغرة...');
      customThumbPath = await uploadTempThumb('pipelineCustomThumb');
    }

    const res = await fetch('/api/pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        username, 
        date, 
        privacy, 
        upload_type: uploadType, 
        channel_id: channelId, 
        force: force,
        publish_at: publishAt,
        skip_first: skipFirst,
        custom_long_title: customLongTitle,
        custom_thumb_path: customThumbPath,
        today_only: todayOnly,
        custom_links: customLinks
      })
    });

    const data = await res.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error);
      return;
    }

    // Hide toast to avoid floating "جاري المعالجة" message for Modal tasks
    document.getElementById('statusSection').classList.remove('visible');
    
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  }

  // Make globally available for inline fallback
  window.handlePipeline = handlePipeline;

  document.getElementById('pipelineForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    console.log("Pipeline Shorts form submitted!");
    handlePipeline('shorts', e.target.querySelector('button[type="submit"]'));
  });
  document.getElementById('btnPipelineLong')?.addEventListener('click', (e) => {
    e.preventDefault();
    console.log("Pipeline Long form submitted!");
    handlePipeline('long', e.currentTarget);
  });

  // === Batch Pipeline ===
  async function runBatchPipeline(uploadType) {
    const skipFirst = parseInt(document.getElementById('batchPipeSkipFirst')?.value) || 0;
    const pipeDateInput = document.getElementById('batchPipeDate');
    const pipeDate = pipeDateInput ? pipeDateInput.value : null;
    try {
      const checkedInputs = document.querySelectorAll('.account-check:checked');
      const checked = [...checkedInputs].map(cb => cb.dataset.username);
      
      if (!checked || !checked.length) {
        alert('لم تقم بتحديد أي حسابات من القائمة الجانبية!');
        showStatus('error', 'حدّد حسابات من القائمة الجانبية أولاً');
        return;
      }
      
      const channelSelect = document.getElementById('batchPipeChannel');
      const channelId = channelSelect ? channelSelect.value : null;
      if (!channelId) {
        alert('لم تقم باختيار قناة يوتيوب الموحدة للعملية! تأكد من القائمة المنسدلة.');
        showStatus('error', 'الرجاء اختيار قناة اليوتيوب الموحدة');
        return;
      }
      const privacy = document.getElementById('batchPipePrivacy')?.value || 'private';
      const force = document.getElementById('batchPipeForce')?.checked || false;
      const publishAt = document.getElementById('batchPipePublishAt')?.value || null;
      const todayOnly = document.getElementById('batchPipeTodayOnly')?.checked || false;

      // Check channel only if NOT prepare
      if (uploadType !== 'prepare' && !channelId) {
        alert('لم تقم باختيار قناة يوتيوب الموحدة للعملية! تأكد من القائمة المنسدلة.');
        showStatus('error', 'الرجاء اختيار قناة اليوتيوب الموحدة');
        return;
      }
      
      let btnId = 'btnBatchPipeline';
      if (uploadType === 'long') btnId = 'btnBatchPipelineLong';
      if (uploadType === 'both') btnId = 'btnBatchPipelineBoth';
      if (uploadType === 'prepare') btnId = 'btnBatchPipelinePrepare';
      
      const btn = btnId ? document.getElementById(btnId) : null;
      
      let typeLabel = 'Shorts';
      if (uploadType === 'long') typeLabel = 'فيديو طويل';
      if (uploadType === 'both') typeLabel = 'Shorts + فيديو طويل';
      if (uploadType === 'prepare') typeLabel = 'تحميل ودمج فقط';

      let confirmMsg = `سيتم تشغيل المسار الكامل (تحميل + دمج + رفع) لـ ${checked.length} حسابات (${typeLabel}). هل أنت متأكد؟`;
      if (uploadType === 'prepare') confirmMsg = `سيتم تحميل ودمج السنابات لـ ${checked.length} حسابات (بدون رفع يوتيوب حالياً). هل أنت متأكد؟`;

      if (!confirm(confirmMsg)) return;
      
      const customTitleInput = document.getElementById('batchPipeCustomTitle');
      const customLongTitle = customTitleInput ? customTitleInput.value : null;

      setLoading(btn, true);
      
      let customThumbPath = null;
      if (document.getElementById('batchPipeCustomThumb')?.files?.length > 0) {
        showStatus('running', 'جاري رفع الصورة المصغرة...');
        customThumbPath = await uploadTempThumb('batchPipeCustomThumb');
      }
      const res = await fetch('/api/run-all-pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          usernames: checked, 
          upload_type: uploadType, 
          channel_id: channelId, 
          privacy: privacy, 
          force: force,
          publish_at: publishAt,
          skip_first: skipFirst,
          date: pipeDate,
          custom_long_title: customLongTitle,
          custom_thumb_path: customThumbPath,
          today_only: todayOnly
        })
      });
      
      const data = await res.json();
      if (!data.ok) {
        setLoading(btn, false);
        alert('حدث خطأ من الخادم: ' + data.error);
        showStatus('error', data.error);
        return;
      }
      
      // Hide old toast message since we use Modal now
      document.getElementById('statusSection').classList.remove('visible');
      
      pollTask(data.task_id, () => {
        setLoading(btn, false);
        refreshMergedFolders();
      });
    } catch(err) {
      alert("حدث خطأ برمجي أثناء الضغط على الزر: " + err.message);
      console.error(err);
    }
  }

  const btnBatch1 = document.getElementById('btnBatchPipeline');
  const btnBatch2 = document.getElementById('btnBatchPipelineLong');
  
  // Make the function accessible globally so inline onclick works as a fallback!
  window.runBatchPipeline = runBatchPipeline;
  
  if(btnBatch1) {
      btnBatch1.addEventListener('click', (e) => { e.preventDefault(); console.log("Batch Shorts clicked!"); runBatchPipeline(false); });
  } else {
      console.error("زر Batch غير موجود في DOM");
  }
  
  if(btnBatch2) {
      btnBatch2.addEventListener('click', (e) => { e.preventDefault(); console.log("Batch Long clicked!"); runBatchPipeline(true); });
  } else {
      console.error("زر Batch الطويل غير موجود في DOM");
  }

  // === Upload all ===
  document.getElementById('uploadAll')?.addEventListener('click', async () => {
    const btn = document.getElementById('uploadAll');
    const res = await fetch('/api/merged-folders');
    const folders = await res.json();
    if (!folders.length) {
      showStatus('error', 'لا توجد مجلدات مدمجة للرفع');
      return;
    }
    const privacy = document.getElementById('uploadPrivacy')?.value || 'private';
    const uploadType = document.getElementById('uploadType')?.value || 'shorts';
    const channelId = document.getElementById('bulkUploadChannel')?.value || null;

    if (!channelId) {
      showStatus('error', 'الرجاء اختيار القناة لرفع الفيديوهات إليها');
      return;
    }

    setLoading(btn, true);
    const postRes = await fetch('/api/upload-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folders, privacy, upload_type: uploadType, channel_id: channelId || undefined }),
    });
    const data = await postRes.json();
    if (!data.ok) {
      setLoading(btn, false);
      showStatus('error', data.error || 'خطأ');
      return;
    }
    showStatus('running', 'جاري رفع الكل...');
    pollTask(data.task_id, () => {
      setLoading(btn, false);
      refreshMergedFolders();
    });
  });

  // === Clear batch ===
  document.getElementById('clearBatchBtn')?.addEventListener('click', async () => {
    const sel = document.getElementById('clearFolder');
    const opt = sel?.options[sel.selectedIndex];
    const username = opt?.value;
    if (!username || !date) {
      showStatus('error', 'اختر مجلداً للمسح');
      return;
    }
    if (!confirm(`حذف ${username}/${date} نهائياً؟`)) return;
    const res = await fetch('/api/clear-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date }),
    });
    const data = await res.json();
    if (data.ok) {
      showStatus('done', data.message);
      refreshMergedFolders();
    } else {
      showStatus('error', data.error);
    }
  });

  // === TikTok Manual Bridge ===
  const tiktokFolder = document.getElementById('tiktokFolder');

  document.getElementById('openFolderBtn')?.addEventListener('click', async () => {
    const opt = tiktokFolder?.options[tiktokFolder.selectedIndex];
    const username = opt?.value;
    const date = opt?.dataset?.date;

    if (!username) {
      showStatus('error', 'اختر مجلداً أولاً');
      return;
    }

    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, date }),
    });
    const data = await res.json();
    if (!data.ok) {
      showStatus('error', data.error);
    }
  });

  document.getElementById('copyCaptionBtn')?.addEventListener('click', () => {
    const opt = tiktokFolder?.options[tiktokFolder.selectedIndex];
    const username = opt?.value;

    if (!username) {
      showStatus('error', 'اختر مجلداً أولاً');
      return;
    }

    const caption = `Snapchat Story from ${username} #snapchat #story #fyp #viral`;
    navigator.clipboard.writeText(caption).then(() => {
      showStatus('done', 'تم نسخ العنوان!');
    }).catch(() => {
      showStatus('error', 'فشل النسخ');
    });
  });

  // === Army Bulk Connect ===
  document.getElementById('btnBulkConnect')?.addEventListener('click', () => {
    const idleSoldiers = [...document.querySelectorAll('.soldier-card')].filter(card => {
        return card.innerText.includes('غير مفعل') || card.innerText.includes('IDLE');
    });

    if (idleSoldiers.length === 0) {
        showStatus('done', 'كافة الجنود نشطون بالفعل! 💪');
        return;
    }

    if (!confirm(`سيتم فتح ${idleSoldiers.length} صفحات لربط الجنود دفعة واحدة. هل تريد الاستمرار؟`)) return;

    let opened = 0;
    idleSoldiers.forEach((card, index) => {
        const nameNode = card.querySelector('strong');
        const name = nameNode ? nameNode.innerText.replace('جندي:', '').trim() : '';
        if (name) {
            setTimeout(() => {
                window.open(`/youtube/connect?soldier=${encodeURIComponent(name)}`, '_blank');
            }, index * 800);
            opened++;
        }
    });
    
    showStatus('running', `جاري فتح ${opened} واجهات للربط... يرجى تأكيد الحساب في كل صفحة.`);
  });

  // === Tabs Logic ===
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  function switchTab(tabId) {
    if (!tabId) return;
    tabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    tabPanes.forEach(pane => {
      pane.classList.toggle('active', pane.id === tabId);
    });
    localStorage.setItem('snapscrap_active_tab', tabId);
    
    if (tabId === 'tab-army' && typeof fetchTokenStatus === 'function') {
        fetchTokenStatus();
    }
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  const savedTab = localStorage.getItem('snapscrap_active_tab');
  if (savedTab && document.getElementById(savedTab)) {
    switchTab(savedTab);
  } else {
    switchTab('tab-download');
  }

  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href && href.startsWith('#section-')) {
          const sectionId = href.replace('#', '');
          const targetCard = document.getElementById(sectionId);
          if (targetCard) {
              const parentPane = targetCard.closest('.tab-pane');
              if (parentPane) switchTab(parentPane.id);
          }
      }
    });
  });

  // === Army Token Health ===
  window.fetchTokenStatus = async function() {
      const tbody = document.getElementById('tokenStatusBody');
      if(!tbody) return;
      try {
          const res = await fetch('/api/youtube/token_status');
          const data = await res.json();
          if(!data.ok) return;
          
          if(data.tokens.length === 0) {
              tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;'>لا توجد ملفات توكن حالياً.</td></tr>";
              return;
          }
          
          tbody.innerHTML = "";
          data.tokens.forEach(t => {
              const tr = document.createElement('tr');
              let statusClass = "badge-done";
              let statusText = "نشط ✅";
              
              if(t.status === 'cooldown') {
                  statusClass = "badge-queued";
                  statusText = "استراحة ⏳";
              } else if(t.status === 'invalid') {
                  statusClass = "badge-error";
                  statusText = "معطل 💀";
              }
              
              const cooldownStr = t.cooldown_until ? new Date(t.cooldown_until).toLocaleString('ar-DZ') : "-";
              
              tr.innerHTML = `
                  <td>${t.id}</td>
                  <td><span class="history-status-badge ${statusClass}">${statusText}</span></td>
                  <td>${cooldownStr}</td>
                  <td>
                      <button class="btn btn-secondary btn-sm" onclick="deleteSingleToken('${t.id}')" title="حذف الملف">
                          <i class="fa-solid fa-trash"></i>
                      </button>
                  </td>
              `;
              tbody.appendChild(tr);
          });
      } catch(e) { console.error(e); }
  };

  window.deleteSingleToken = async function(tokenId) {
      if(!confirm(`هل أنت متأكد من حذف ملف التوكن ${tokenId}؟`)) return;
      try {
          const res = await fetch(`/api/youtube/delete_token/${tokenId}`, { 
              method: 'DELETE',
              headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
          });
          const data = await res.json();
          if(data.ok) {
              fetchTokenStatus();
              showStatus('done', 'تم حذف التوكن بنجاح');
          }
      } catch(e) { console.error(e); }
  };

  // === Thumbnail Preview ===
  window.previewThumbnail = async function(source) {
      const modal = document.getElementById('thumbnailModal');
      const container = document.getElementById('thumbnailPreviewContainer');
      const img = document.getElementById('thumbnailPreviewImg');
      
      let username = "";
      let date = "";
      
      if(source === 'pipeline') {
          username = document.getElementById('pipelineUsername')?.options[document.getElementById('pipelineUsername').selectedIndex]?.value;
          date = document.getElementById('pipelineDate')?.value;
      } else {
          username = document.getElementById('uploadUsername')?.value;
          date = document.getElementById('uploadDate')?.value;
      }
      
      if(!username) {
          showStatus('error', 'يرجى اختيار اسم المستخدم أولاً');
          return;
      }
      
      modal.classList.add('visible');
      modal.setAttribute('aria-hidden', 'false');
      container.style.display = 'block';
      img.style.display = 'none';
      
      try {
          const res = await fetch('/api/thumbnail/preview', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ username, date })
          });
          const data = await res.json();
          if(data.ok) {
              img.src = "data:image/jpeg;base64," + data.image;
              img.style.display = 'block';
              container.style.display = 'none';
          } else {
              showStatus('error', data.error || 'فشل توليد المعاينة');
              closeThumbnailModal();
          }
      } catch(e) {
          console.error(e);
          showStatus('error', 'خطأ في الاتصال');
          closeThumbnailModal();
      }
  };

  // Initial fetch for tokens if on army tab
  setTimeout(fetchTokenStatus, 2000);
});

