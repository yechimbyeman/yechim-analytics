"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, FileText, MessageCircle, MessagesSquare, Package, Users, Eye, Heart, Reply, LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

type MemberRow = { id: string; external_user_id: string; username: string | null; display_name: string | null; is_staff: boolean; is_bot: boolean };
type MessageRow = { id: string; member_id: string | null; message_kind: string; sent_at: string; reply_to_external_message_id: string | null; views_count: number | null; reactions: Record<string, number> | null; raw_metadata: Record<string, unknown> | null; body: string | null; permalink: string | null };
type SourceRow = { id: string; title: string };
const CHAT_ID = "2100556847";
const BASE = "/yechim-analytics";

function shiftedDate(value: string) { return new Date(new Date(value).getTime() + 5 * 60 * 60 * 1000); }
function formatNumber(value: number) { return new Intl.NumberFormat("ru-RU").format(value); }
function initials(value: string) { return value.trim().split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase() || "К"; }

export default function Dashboard() {
  const [messages, setMessages] = useState<MessageRow[]>([]);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [source, setSource] = useState<SourceRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const supabase = createClient();
      try {
        const { data: { user }, error: authError } = await supabase.auth.getUser();
        if (authError || !user) { window.location.replace(`${BASE}/login/`); return; }
        const { data: access, error: accessError } = await supabase.from("app_access").select("user_id").eq("user_id", user.id).maybeSingle();
        if (accessError || !access) {
          await supabase.auth.signOut();
          window.location.replace(`${BASE}/login/?error=unauthorized`);
          return;
        }

        const { data: sourceData, error: sourceError } = await supabase.from("sources").select("id,title").eq("platform", "telegram").eq("external_source_id", CHAT_ID).eq("is_active", true).maybeSingle();
        if (sourceError) throw sourceError;
        if (!sourceData) {
          if (!cancelled) { setSource(null); setLoadError("Активный источник Yechim Chat не найден."); }
          return;
        }
        const sourceRow = sourceData as SourceRow;
        let allMessages: MessageRow[] = [];
        const pageSize = 1000;
        for (let from = 0; ; from += pageSize) {
          const { data, error } = await supabase.from("messages")
            .select("id,member_id,message_kind,sent_at,reply_to_external_message_id,views_count,reactions,raw_metadata,body,permalink")
            .eq("source_id", sourceRow.id).order("sent_at", { ascending: true }).range(from, from + pageSize - 1);
          if (error) throw error;
          const batch = (data ?? []) as MessageRow[];
          allMessages = allMessages.concat(batch);
          if (batch.length < pageSize) break;
        }
        const { data: memberData, error: memberError } = await supabase.from("chat_members")
          .select("id,external_user_id,username,display_name,is_staff,is_bot").eq("source_id", sourceRow.id);
        if (memberError) throw memberError;
        if (!cancelled) { setSource(sourceRow); setMessages(allMessages); setMembers((memberData ?? []) as MemberRow[]); }
      } catch (error) {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : "Не удалось загрузить данные.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  const memberMap = useMemo(() => new Map(members.map((member) => [member.id, member])), [members]);
  const customerMessages = messages.filter((message) => { const member = message.member_id ? memberMap.get(message.member_id) : undefined; return message.message_kind === "message" && !!member && !member.is_staff && !member.is_bot; });
  const staffMessages = messages.filter((message) => { const member = message.member_id ? memberMap.get(message.member_id) : undefined; return !!member?.is_staff; });
  const botMessages = messages.filter((message) => { const member = message.member_id ? memberMap.get(message.member_id) : undefined; return !!member?.is_bot; });
  const uniqueCustomers = new Set(customerMessages.map((message) => message.member_id)).size;
  const replies = messages.filter((message) => !!message.reply_to_external_message_id).length;
  const publications = messages.filter((message) => message.message_kind === "publication" || message.raw_metadata?.is_advertising_account === true);
  const staffPostCandidates = messages.filter((message) => message.raw_metadata?.is_staff_authored_non_reply === true && message.raw_metadata?.is_advertising_account !== true).length;
  const withViews = messages.filter((message) => message.views_count !== null).length;
  const withReactions = messages.filter((message) => !!message.reactions && Object.keys(message.reactions).length > 0).length;

  const now = new Date();
  const monthLabels: string[] = [];
  const monthValues: number[] = [];
  for (let offset = 10; offset >= 0; offset--) {
    const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - offset, 1));
    const key = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
    monthLabels.push(new Intl.DateTimeFormat("ru-RU", { month: "short" }).format(date).replace(".", ""));
    monthValues.push(customerMessages.filter((message) => { const shifted = shiftedDate(message.sent_at); return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}` === key; }).length);
  }
  const maxMonth = Math.max(1, ...monthValues);
  const publicationMonthValues = monthLabels.map((_, index) => {
    const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - (10 - index), 1));
    const key = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
    return publications.filter((message) => { const shifted = shiftedDate(message.sent_at); return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}` === key; }).length;
  });
  const recentPublications = [...publications].sort((a, b) => b.sent_at.localeCompare(a.sent_at)).slice(0, 12);
  const clientCounts = new Map<string, number>();
  for (const message of customerMessages) if (message.member_id) clientCounts.set(message.member_id, (clientCounts.get(message.member_id) ?? 0) + 1);
  const topClients = [...clientCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([id, count]) => {
    const member = memberMap.get(id);
    return { id, count, name: member?.display_name || (member?.username ? `@${member.username}` : `Клиент ${member?.external_user_id ?? ""}`), username: member?.username };
  });
  const cards = [
    ["Клиенты", uniqueCustomers, "Уникальные авторы сообщений", Users],
    ["Сообщения клиентов", customerMessages.length, "Сообщения от клиентов", MessageCircle],
    ["Сообщения команды", staffMessages.length, "Участники, отмеченные как сотрудники", MessagesSquare],
    ["Ответы в чате", replies, "Сообщения с reply-связью", Reply],
  ] as const;

  async function signOut() {
    await createClient().auth.signOut();
    window.location.assign(`${BASE}/login/`);
  }

  if (loading) return <main className="login-wrap"><section className="login-card"><div className="brand">YECHIM<small>ANALYTICS PLATFORM</small></div><h1 className="h1">Загружаем аналитику…</h1><p className="sub">Проверяем доступ и загружаем историю Yechim Chat.</p></section></main>;

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand">YECHIM<small>ANALYTICS PLATFORM</small></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="nav">
        <a className="active" href={`${BASE}/dashboard/`}><BarChart3 size={17}/>Обзор</a>
        <a href="#clients"><Users size={17}/>Клиенты</a><a href="#requests"><MessagesSquare size={17}/>Запросы</a><a href="#posts"><FileText size={17}/>Публикации</a><a href="#products"><Package size={17}/>Интерес к товарам</a>
      </nav>
      <div className="nav-label">PLATFORMS</div>
      <nav className="nav"><a href="#telegram"><MessageCircle size={17}/>Telegram</a><a href="#instagram"><Activity size={17}/>Instagram · позже</a></nav>
      <div className="sidebar-foot">Закрытая аналитическая система YECHIM.<br/>Доступ ограничен одним аккаунтом.</div>
    </aside>
    <main className="main">
      <header className="topline">
        <div><div className="eyebrow">MARKETING INTELLIGENCE / TELEGRAM</div><h1 className="h1">Обзор аналитики</h1><div className="sub">Данные только из группы Yechim Chat · ID {CHAT_ID}</div></div>
        <button className="login-btn" style={{width:"auto",marginTop:0,padding:"10px 14px"}} onClick={signOut}><LogOut size={15}/> Выйти</button>
      </header>
      {loadError && <div className="notice warning">Не удалось полностью загрузить данные: {loadError}</div>}
      {!source && !loadError && <div className="notice warning">Активный источник Yechim Chat не найден. Проверьте подключение источника в базе.</div>}
      <div className="grid-kpi">{cards.map(([label,value,note,Icon]) => <section className="card" key={label}><div className="kpi-top"><span>{label}</span><Icon size={17}/></div><div className="kpi-value">{formatNumber(value)}</div><div className="kpi-note">{note}</div></section>)}</div>
      <div className="content-grid">
        <section className="card"><div className="section-head"><div><h2 className="card-title">Активность клиентов по месяцам</h2><div className="card-desc">Количество сообщений клиентов · UTC+5</div></div><span className="tag blue">11 месяцев</span></div>
          <div className="live-chart">{monthValues.map((value,index) => <div className="live-bar-col" key={monthLabels[index]}><div className="live-bar-value">{value || ""}</div><div className="live-bar-track"><div className="live-bar" style={{height:`${Math.max(value > 0 ? 5 : 0, value / maxMonth * 100)}%`}} /></div><div className="live-bar-label">{monthLabels[index]}</div></div>)}</div>
          <div className="chart-foot">Всего сообщений клиентов за выбранную историю: <b>{formatNumber(customerMessages.length)}</b></div>
        </section>
        <section className="card" id="telegram"><h2 className="card-title">Источник данных</h2><div className="card-desc">Активный источник аналитики</div>
          <div className="source-row"><MessageCircle size={19}/><div><b>{source?.title ?? "Yechim Chat"}</b><small>Telegram · {CHAT_ID}</small></div><span className="tag">Активен</span></div>
          <div className="mini-stats"><div><span>Все сообщения</span><b>{formatNumber(messages.length)}</b></div><div><span>Сообщения ботов</span><b>{formatNumber(botMessages.length)}</b></div><div><span>Публикации Telegram</span><b>{formatNumber(publications.length)}</b></div></div>
          <p className="empty-note">Другие группы и личные чаты в этот Dashboard не включаются.</p>
        </section>
      </div>
      <div className="content-grid lower-grid">
        <section className="card" id="clients"><div className="section-head"><div><h2 className="card-title">Самые активные клиенты</h2><div className="card-desc">По количеству сообщений в Yechim Chat</div></div></div>
          {topClients.length ? <div className="rank-list">{topClients.map((client,index) => <div className="rank-row" key={client.id}><span className="rank-num">{index+1}</span><span className="avatar">{initials(client.name)}</span><div className="rank-name"><b>{client.name}</b><small>{client.username ? `@${client.username}` : "Участник Telegram"}</small></div><strong>{formatNumber(client.count)}</strong></div>)}</div> : <p className="empty-note">Пока нет сообщений от клиентов.</p>}
        </section>
        <section className="card" id="requests"><h2 className="card-title">Качество и классификация данных</h2><div className="card-desc">Что уже доступно в истории</div>
          <div className="metric-list"><div><Reply size={16}/><span>Сообщения с ответами</span><b>{formatNumber(replies)}</b></div><div><Eye size={16}/><span>Сообщения с данными о просмотрах</span><b>{formatNumber(withViews)}</b></div><div><Heart size={16}/><span>Сообщения с реакциями</span><b>{formatNumber(withReactions)}</b></div><div><Users size={16}/><span>Сообщения команды</span><b>{formatNumber(staffMessages.length)}</b></div></div>
          <p className="empty-note">Категории запросов пока не рассчитаны: следующим этапом добавим классификацию обращений и тем.</p>
        </section>
      </div>
      <section className="card" id="posts" style={{marginTop:16}}>
        <div className="section-head"><div><h2 className="card-title">Публикации и рекламная активность</h2><div className="card-desc">Публикации @yechimbor отдельно от обращений клиентов · UTC+5</div></div></div>
        <div className="post-grid"><div><span>Распознано публикаций</span><b>{formatNumber(publications.length)}</b></div><div><span>Сообщения команды без ответа · кандидаты для проверки</span><b>{formatNumber(staffPostCandidates)}</b></div><div><span>Сообщения с просмотрами</span><b>{formatNumber(withViews)}</b></div></div>
        <div className="section-head" style={{marginTop:20}}><div><h3 className="card-title">Публикации по месяцам</h3><div className="card-desc">Количество постов от @yechimbor</div></div></div>
        <div className="live-chart">{publicationMonthValues.map((value,index) => <div className="live-bar-col" key={`post-${monthLabels[index]}`}><div className="live-bar-value">{value || ""}</div><div className="live-bar-track"><div className="live-bar" style={{height:`${Math.max(value > 0 ? 5 : 0, value / Math.max(1,...publicationMonthValues) * 100)}%`}} /></div><div className="live-bar-label">{monthLabels[index]}</div></div>)}</div>
        <div className="section-head" style={{marginTop:20}}><div><h3 className="card-title">Последние рекламные публикации</h3><div className="card-desc">Текст, дата и ссылка на оригинал в Telegram</div></div></div>
        {recentPublications.length ? <div className="rank-list">{recentPublications.map((post) => <div className="rank-row" key={post.id} style={{alignItems:"flex-start"}}><div className="rank-name"><b>{new Date(post.sent_at).toLocaleString("ru-RU", {timeZone:"Asia/Tashkent"})}</b><small>{(post.body || "Публикация с медиа").slice(0,220)}</small>{post.permalink && <a href={post.permalink} target="_blank" rel="noreferrer">Открыть пост в Telegram ↗</a>}<small>{post.raw_metadata?.media_type === "photo" ? "Фото" : post.raw_metadata?.media_type === "video" ? "Видео" : post.raw_metadata?.has_media ? "Медиа" : "Текстовая публикация"}</small></div></div>)}</div> : <p className="empty-note">Публикации пока не найдены.</p>}
      </section>
      <p className="empty-note">YECHIM Analytics · статистика обновляется после импорта Telegram. Данные других источников исключены.</p>
    </main>
  </div>;
}
