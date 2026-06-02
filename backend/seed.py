"""
Seed script — populates MongoDB with demo data matching the old CSV data.
Images use public CDN URLs (no Cloudinary upload needed).

Usage:
    python seed.py            # seed if not already seeded
    python seed.py --reset    # clear all collections first, then seed
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bcrypt
from datetime import datetime, timedelta
from app.database.mongo_db import db


# ── Helpers ───────────────────────────────────────────────────────────────────

def pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def ts(days_ago=0, hours_ago=0, minutes_ago=0):
    dt = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
    return dt.isoformat() + 'Z'

def avatar(name):
    encoded = name.replace(' ', '+')
    return f"https://ui-avatars.com/api/?name={encoded}&background=7c3aed&color=fff&bold=true&size=128"

def cover(seed_word):
    return f"https://picsum.photos/seed/{seed_word}/800/400"


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset_all():
    collections = [
        db.users, db.blogs, db.blog_likes, db.comments,
        db.user_follows, db.follow_requests, db.messages,
        db.groups, db.group_members, db.notifications,
        db.push_subscriptions,
    ]
    for col in collections:
        col._col.delete_many({})
    print("All collections cleared.")


# ── Seed ──────────────────────────────────────────────────────────────────────

def seed():
    # ── Users ─────────────────────────────────────────────────────────────────
    print("Creating users...")

    admin = db.users.insert({
        'name': 'Admin User',
        'email': 'admin@demo.com',
        'password_hash': pw('password123'),
        'bio': 'Platform administrator.',
        'profile_pic': avatar('Admin User'),
        'role': 'admin',
        'is_active': 'True',
        'updated_at': ts(30),
        'created_at': ts(30),
    })

    alice = db.users.insert({
        'name': 'Alice Johnson',
        'email': 'alice@demo.com',
        'password_hash': pw('password123'),
        'bio': 'Full-stack developer. Love React and Python. Writing about tech and life.',
        'profile_pic': avatar('Alice Johnson'),
        'role': 'user',
        'is_active': 'True',
        'updated_at': ts(25),
        'created_at': ts(25),
    })

    bob = db.users.insert({
        'name': 'Bob Smith',
        'email': 'bob@demo.com',
        'password_hash': pw('password123'),
        'bio': 'Designer & illustrator. I write about UX, creativity, and minimalism.',
        'profile_pic': avatar('Bob Smith'),
        'role': 'user',
        'is_active': 'True',
        'updated_at': ts(22),
        'created_at': ts(22),
    })

    clara = db.users.insert({
        'name': 'Clara Davis',
        'email': 'clara@demo.com',
        'password_hash': pw('password123'),
        'bio': 'Travel blogger and photographer. Visited 42 countries and counting.',
        'profile_pic': avatar('Clara Davis'),
        'role': 'user',
        'is_active': 'True',
        'updated_at': ts(18),
        'created_at': ts(18),
    })

    david = db.users.insert({
        'name': 'David Lee',
        'email': 'david@demo.com',
        'password_hash': pw('password123'),
        'bio': 'ML engineer and open-source contributor. Obsessed with data.',
        'profile_pic': avatar('David Lee'),
        'role': 'user',
        'is_active': 'True',
        'updated_at': ts(15),
        'created_at': ts(15),
    })

    eva = db.users.insert({
        'name': 'Eva Martinez',
        'email': 'eva@demo.com',
        'password_hash': pw('password123'),
        'bio': 'Startup founder. Writing about entrepreneurship, product, and growth.',
        'profile_pic': avatar('Eva Martinez'),
        'role': 'user',
        'is_active': 'True',
        'updated_at': ts(10),
        'created_at': ts(10),
    })

    users = [admin, alice, bob, clara, david, eva]
    print(f"  ✓ {len(users)} users created")

    # ── Follows ───────────────────────────────────────────────────────────────
    print("Creating follows...")

    follow_pairs = [
        (alice, bob),   (alice, clara), (alice, david),
        (bob, alice),   (bob, eva),     (bob, david),
        (clara, alice), (clara, bob),   (clara, eva),
        (david, alice), (david, eva),   (david, bob),
        (eva, alice),   (eva, clara),   (eva, david),
        (admin, alice), (admin, bob),
    ]
    for follower, followed in follow_pairs:
        db.user_follows.insert({
            'follower_id': follower['id'],
            'followed_id': followed['id'],
        })

    print(f"  ✓ {len(follow_pairs)} follow relationships created")

    # ── Blogs ─────────────────────────────────────────────────────────────────
    print("Creating blogs...")

    blog1 = db.blogs.insert({
        'author_id': alice['id'],
        'title': 'Getting Started with React 18: What You Need to Know',
        'content': '''<h2>React 18 is Here</h2>
<p>React 18 brings a wave of new features that fundamentally change how we build user interfaces. The most exciting addition is <strong>Concurrent Rendering</strong>, which allows React to prepare multiple versions of the UI at the same time.</p>
<h3>Key Features</h3>
<ul>
<li><strong>Automatic Batching</strong> — state updates are batched automatically for better performance</li>
<li><strong>Transitions</strong> — mark updates as non-urgent with <code>startTransition</code></li>
<li><strong>Suspense on the server</strong> — stream HTML from the server progressively</li>
<li><strong>New Hooks</strong> — <code>useId</code>, <code>useTransition</code>, <code>useDeferredValue</code></li>
</ul>
<h3>Upgrading</h3>
<p>The upgrade path is straightforward. Replace <code>ReactDOM.render</code> with the new <code>createRoot</code> API and you're running React 18.</p>
<blockquote>React 18 is the result of years of research into concurrent rendering.</blockquote>
<p>The ecosystem is catching up fast. Most popular libraries have already released React 18-compatible versions. Go ahead and upgrade — you won't regret it.</p>''',
        'cover_image': cover('react18'),
        'visibility': 'public',
        'tags': 'react,javascript,frontend,webdev',
        'template': 'default',
        'shares_count': '14',
        'is_deleted': 'False',
        'updated_at': ts(20),
        'created_at': ts(20),
    })

    blog2 = db.blogs.insert({
        'author_id': bob['id'],
        'title': 'The Minimalist Design Principles Every Developer Should Know',
        'content': '''<h2>Less is More</h2>
<p>Minimalism in design is not about removing features — it's about removing everything that doesn't serve a purpose. As developers, we often focus on functionality but neglect the user's cognitive load.</p>
<h3>Core Principles</h3>
<ol>
<li><strong>White space is your friend</strong> — breathing room between elements reduces cognitive load</li>
<li><strong>Limit your colour palette</strong> — 2-3 colours maximum for a focused experience</li>
<li><strong>Typography hierarchy</strong> — use size and weight to guide the reader's eye</li>
<li><strong>One action per screen</strong> — what do you want the user to do?</li>
</ol>
<h3>Practical Application</h3>
<p>Start by auditing your current UI. For every element, ask: <em>"Would the user miss this if it was gone?"</em> If the answer is no, remove it.</p>
<p>The best interface is the one the user doesn't notice — it just works.</p>''',
        'cover_image': cover('design'),
        'visibility': 'public',
        'tags': 'design,ux,minimalism,frontend',
        'template': 'default',
        'shares_count': '22',
        'is_deleted': 'False',
        'updated_at': ts(17),
        'created_at': ts(17),
    })

    blog3 = db.blogs.insert({
        'author_id': clara['id'],
        'title': 'Backpacking Southeast Asia on a Budget: My 3-Month Journey',
        'content': '''<h2>The Trip That Changed Everything</h2>
<p>Three months, six countries, and less than $3,000. Southeast Asia is one of the most budget-friendly travel destinations in the world — if you know how to do it right.</p>
<h3>Countries I Visited</h3>
<ul>
<li>🇹🇭 Thailand — 3 weeks (Bangkok, Chiang Mai, Koh Tao)</li>
<li>🇻🇳 Vietnam — 4 weeks (Ha Noi to Ho Chi Minh by train)</li>
<li>🇰🇭 Cambodia — 1 week (Siem Reap & Angkor Wat)</li>
<li>🇱🇦 Laos — 2 weeks (Luang Prabang, Vang Vieng)</li>
<li>🇲🇾 Malaysia — 1.5 weeks (KL & Penang)</li>
<li>🇸🇬 Singapore — 3 days (splurged a little!)</li>
</ul>
<h3>Top Budget Tips</h3>
<p>Street food is your best friend. You can eat like a king in Vietnam for $2-3 a meal. Night buses and trains save you hostel costs. Book accommodation only 1-2 days ahead for the best walk-in deals.</p>
<blockquote>The best moments were never the ones I planned. They happened on random buses, in stranger's kitchens, and at sunset on empty beaches.</blockquote>''',
        'cover_image': cover('travel'),
        'visibility': 'public',
        'tags': 'travel,backpacking,asia,budget',
        'template': 'default',
        'shares_count': '38',
        'is_deleted': 'False',
        'updated_at': ts(14),
        'created_at': ts(14),
    })

    blog4 = db.blogs.insert({
        'author_id': david['id'],
        'title': 'Understanding Large Language Models: A Practical Introduction',
        'content': '''<h2>What Are LLMs?</h2>
<p>Large Language Models (LLMs) are neural networks trained on massive text corpora. They learn statistical patterns in language to predict the next token — and that simple objective leads to surprisingly powerful emergent capabilities.</p>
<h3>The Transformer Architecture</h3>
<p>At the heart of every modern LLM is the Transformer, introduced in the 2017 paper <em>"Attention Is All You Need"</em>. The key innovation is the <strong>self-attention mechanism</strong> which allows the model to weigh the importance of different tokens when producing an output.</p>
<h3>Key Concepts</h3>
<ul>
<li><strong>Tokens</strong> — subword units (not words) that the model processes</li>
<li><strong>Context window</strong> — how much text the model can "see" at once</li>
<li><strong>Temperature</strong> — controls randomness in generation</li>
<li><strong>Fine-tuning vs. prompting</strong> — two ways to adapt a model to a task</li>
</ul>
<p>The most important takeaway: LLMs are stochastic text completion engines. Understanding this helps you use them more effectively and understand their limitations.</p>''',
        'cover_image': cover('ai'),
        'visibility': 'public',
        'tags': 'ai,machinelearning,llm,tech',
        'template': 'default',
        'shares_count': '51',
        'is_deleted': 'False',
        'updated_at': ts(11),
        'created_at': ts(11),
    })

    blog5 = db.blogs.insert({
        'author_id': eva['id'],
        'title': 'From Zero to First Customer: What Nobody Tells You About Startups',
        'content': '''<h2>The Unglamorous Truth</h2>
<p>Everyone talks about funding rounds and product launches. Nobody talks about the six months you spend cold-emailing strangers who never reply, or rebuilding your entire product after 20 user interviews reveal your assumptions were completely wrong.</p>
<h3>What Actually Matters</h3>
<ol>
<li><strong>Talk to users before writing a single line of code</strong> — I cannot stress this enough</li>
<li><strong>Revenue > users</strong> — unless you have VC money, focus on paying customers</li>
<li><strong>Do things that don't scale</strong> — manual onboarding, hand-held support, personal emails</li>
<li><strong>Hire slow, fire fast</strong> — the wrong hire can kill a small team</li>
</ol>
<h3>The Moment Everything Changed</h3>
<p>Our first paying customer came from a tweet I almost didn't post. Six months of grinding, and it came down to a 280-character message at 11pm on a Tuesday. That's startups.</p>
<blockquote>Build something 100 people love, not something 1 million people kind of like.</blockquote>''',
        'cover_image': cover('startup'),
        'visibility': 'public',
        'tags': 'startup,entrepreneurship,business,growth',
        'template': 'default',
        'shares_count': '67',
        'is_deleted': 'False',
        'updated_at': ts(8),
        'created_at': ts(8),
    })

    blog6 = db.blogs.insert({
        'author_id': alice['id'],
        'title': 'Python Type Hints: Writing Cleaner, Safer Code',
        'content': '''<h2>Why Type Hints Matter</h2>
<p>Python is dynamically typed, but that doesn't mean you have to give up on type safety. Type hints, introduced in Python 3.5, let you annotate variables and function signatures — and tools like <code>mypy</code> and your IDE use them to catch bugs before runtime.</p>
<h3>Basic Syntax</h3>
<pre><code>def greet(name: str) -> str:
    return f"Hello, {name}"

user_count: int = 0
scores: list[float] = []</code></pre>
<h3>Advanced Patterns</h3>
<ul>
<li><code>Optional[T]</code> — value might be None</li>
<li><code>Union[A, B]</code> — one of multiple types (or use <code>A | B</code> in Python 3.10+)</li>
<li><code>TypedDict</code> — type-annotated dictionaries</li>
<li><code>Protocol</code> — structural subtyping (duck typing + type safety)</li>
</ul>
<p>Start adding type hints to new code today. You don't need 100% coverage — even partial coverage dramatically improves readability and catches real bugs.</p>''',
        'cover_image': cover('python'),
        'visibility': 'public',
        'tags': 'python,typing,backend,programming',
        'template': 'default',
        'shares_count': '29',
        'is_deleted': 'False',
        'updated_at': ts(6),
        'created_at': ts(6),
    })

    blog7 = db.blogs.insert({
        'author_id': bob['id'],
        'title': 'My Figma Workflow for Designing at Speed',
        'content': '''<h2>Design Fast Without Cutting Corners</h2>
<p>After 5 years of designing products, I've settled on a Figma workflow that lets me go from blank canvas to handoff-ready specs in hours, not days.</p>
<h3>The Core Setup</h3>
<ul>
<li><strong>Component library first</strong> — build atoms before molecules, always</li>
<li><strong>Auto-layout everything</strong> — if a frame doesn't have auto-layout, ask yourself why</li>
<li><strong>Variables for colours and spacing</strong> — since Figma 2023, there's no excuse not to</li>
</ul>
<h3>My Daily Shortcuts</h3>
<p>I use <code>K</code> to scale, <code>Ctrl+D</code> to duplicate, and the component search constantly. The biggest productivity unlock was learning to use the keyboard for everything — mouse clicks are expensive.</p>''',
        'cover_image': cover('figma'),
        'visibility': 'public',
        'tags': 'design,figma,workflow,ui',
        'template': 'default',
        'shares_count': '18',
        'is_deleted': 'False',
        'updated_at': ts(4),
        'created_at': ts(4),
    })

    blog8 = db.blogs.insert({
        'author_id': david['id'],
        'title': 'Notes on MongoDB Aggregation Pipelines',
        'content': '''<h2>Beyond Find()</h2>
<p>Most developers use MongoDB's <code>find()</code> for 90% of queries. But for anything analytical — grouping, joining, transforming — the aggregation pipeline is where the real power lies.</p>
<h3>The Basic Stages</h3>
<ul>
<li><code>$match</code> — filter documents (like WHERE)</li>
<li><code>$group</code> — group and aggregate (like GROUP BY)</li>
<li><code>$project</code> — reshape documents (like SELECT)</li>
<li><code>$lookup</code> — join collections (like JOIN)</li>
<li><code>$sort</code>, <code>$limit</code>, <code>$skip</code> — pagination and ordering</li>
</ul>
<h3>Example Pipeline</h3>
<pre><code>db.orders.aggregate([
  { $match: { status: "completed" } },
  { $group: { _id: "$user_id", total: { $sum: "$amount" } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
])</code></pre>
<p>This returns your top 10 customers by order value in milliseconds, even on millions of records.</p>''',
        'cover_image': cover('database'),
        'visibility': 'public',
        'tags': 'mongodb,database,backend,programming',
        'template': 'default',
        'shares_count': '33',
        'is_deleted': 'False',
        'updated_at': ts(2),
        'created_at': ts(2),
    })

    blogs = [blog1, blog2, blog3, blog4, blog5, blog6, blog7, blog8]
    print(f"  ✓ {len(blogs)} blogs created")

    # ── Likes ─────────────────────────────────────────────────────────────────
    print("Creating likes...")

    like_data = [
        (bob,   blog1), (clara, blog1), (david, blog1), (eva,   blog1),
        (alice, blog2), (clara, blog2), (david, blog2), (eva,   blog2), (admin, blog2),
        (alice, blog3), (bob,   blog3), (david, blog3), (eva,   blog3),
        (alice, blog4), (bob,   blog4), (clara, blog4), (eva,   blog4), (admin, blog4),
        (alice, blog5), (bob,   blog5), (clara, blog5), (david, blog5), (admin, blog5),
        (bob,   blog6), (clara, blog6), (david, blog6), (eva,   blog6),
        (alice, blog7), (clara, blog7), (david, blog7), (eva,   blog7),
        (alice, blog8), (bob,   blog8), (clara, blog8), (eva,   blog8), (admin, blog8),
    ]
    for user, blog in like_data:
        db.blog_likes.insert({'blog_id': blog['id'], 'user_id': user['id']})

    print(f"  ✓ {len(like_data)} likes created")

    # ── Comments ──────────────────────────────────────────────────────────────
    print("Creating comments...")

    comment_data = [
        (bob,   blog1, "Great overview! The automatic batching improvement alone was worth the upgrade for us.", ts(19, 2)),
        (david, blog1, "The concurrent features are underrated. startTransition made our data table feel instant.", ts(19, 1)),
        (eva,   blog1, "Still on React 17 but this convinced me to finally upgrade. Thanks!", ts(18, 3)),
        (alice, blog2, "The 'one action per screen' rule is one I keep coming back to. So simple, so effective.", ts(16, 4)),
        (eva,   blog2, "Applied this to our onboarding flow last month. Conversion rate went up 18%.", ts(16, 2)),
        (alice, blog3, "Angkor Wat at sunrise is life-changing. Did you do the temple run?", ts(13, 5)),
        (bob,   blog3, "The Luang Prabang section — YES. Most underrated city in Southeast Asia.", ts(13, 3)),
        (david, blog3, "Bookmarking this for my trip next year. How did you manage visas?", ts(13, 1)),
        (alice, blog4, "The temperature explanation is the clearest I've seen. Most people just say 'creativity'.", ts(10, 2)),
        (bob,   blog4, "Context windows are still my biggest confusion point. Do you have a follow-up post planned?", ts(10, 1)),
        (clara, blog5, "The 'talk to users first' advice sounds obvious until you realise everyone ignores it.", ts(7, 6)),
        (david, blog5, "That cold email grind is so real. Congrats on the first customer moment.", ts(7, 3)),
        (bob,   blog5, "The Paul Graham quote at the end is perfect. Following you for more startup content.", ts(7, 1)),
        (bob,   blog6, "TypedDict changed how I write Flask routes. Such an underused feature.", ts(5, 2)),
        (clara, blog6, "Protocol is the one I always forget exists. Great reminder.", ts(5, 1)),
        (alice, blog7, "Variables in Figma were a game changer for dark mode theming. Great workflow.", ts(3, 4)),
        (clara, blog7, "The auto-layout tip is everything. I refuse to design without it now.", ts(3, 2)),
        (alice, blog8, "$lookup vs embedded documents — would love a follow-up on when to use each.", ts(1, 3)),
        (bob,   blog8, "This pipeline example is exactly what I needed for a dashboard I'm building.", ts(1, 1)),
        (clara, blog8, "Aggregation pipelines scared me until I read this. The stage-by-stage breakdown helps a lot.", ts(0, 4)),
    ]
    for user, blog, text, created in comment_data:
        db.comments.insert({
            'blog_id': blog['id'],
            'author_id': user['id'],
            'text': text,
            'created_at': created,
        })

    print(f"  ✓ {len(comment_data)} comments created")

    # ── Notifications ─────────────────────────────────────────────────────────
    print("Creating notifications...")

    notif_data = [
        (alice, bob,   'follow_accept', "Bob Smith accepted your follow request",   '',       ts(22)),
        (alice, clara, 'follow_accept', "Clara Davis accepted your follow request", '',       ts(18)),
        (bob,   alice, 'like',          "Alice Johnson liked your blog",             blog2['id'], ts(16, 4)),
        (bob,   eva,   'like',          "Eva Martinez liked your blog",              blog2['id'], ts(16, 2)),
        (alice, bob,   'comment',       "Bob Smith commented on your blog",          blog1['id'], ts(19, 2)),
        (alice, david, 'comment',       "David Lee commented on your blog",          blog1['id'], ts(19, 1)),
        (clara, alice, 'like',          "Alice Johnson liked your blog",             blog3['id'], ts(13, 5)),
        (david, alice, 'like',          "Alice Johnson liked your blog",             blog4['id'], ts(10, 2)),
        (eva,   alice, 'like',          "Alice Johnson liked your blog",             blog5['id'], ts(7, 6)),
        (eva,   bob,   'share',         "Bob Smith shared your blog",                blog5['id'], ts(6)),
    ]
    for recipient, sender, ntype, message, blog_id, created in notif_data:
        db.notifications.insert({
            'recipient_id': recipient['id'],
            'sender_id':    sender['id'],
            'type':         ntype,
            'blog_id':      blog_id,
            'message':      message,
            'is_read':      'False',
            'created_at':   created,
        })

    print(f"  ✓ {len(notif_data)} notifications created")

    # ── Messages ──────────────────────────────────────────────────────────────
    print("Creating messages...")

    msg_data = [
        (alice, bob,   "Hey Bob! Loved your minimalism post.",               ts(16, 3, 30)),
        (bob,   alice, "Thanks Alice! Your React 18 post was super helpful.", ts(16, 3, 15)),
        (alice, bob,   "We should collaborate on something some time!",       ts(16, 3,  5)),
        (bob,   alice, "Absolutely, I'd be down for that.",                    ts(16, 2, 50)),
        (eva,   alice, "Your startup post really resonated with me.",          ts(7, 2, 40)),
        (alice, eva,   "Thanks Eva! How's your product coming along?",         ts(7, 2, 20)),
        (eva,   alice, "Slow but steady. Hoping to launch next month.",        ts(7, 2,  5)),
        (david, clara, "Great travel blog! Did you use a travel agent?",       ts(13, 2, 30)),
        (clara, david, "No agent — everything booked on the fly. More fun!",   ts(13, 2, 10)),
    ]
    for sender, receiver, text, created in msg_data:
        db.messages.insert({
            'sender_id':   sender['id'],
            'receiver_id': receiver['id'],
            'group_id':    '',
            'text':        text,
            'is_group':    'False',
            'is_read':     'True',
            'created_at':  created,
        })

    print(f"  ✓ {len(msg_data)} messages created")

    # ── Group chat ────────────────────────────────────────────────────────────
    print("Creating group chat...")

    group = db.groups.insert({
        'name':        'Bloggers Hub',
        'description': 'A place for all bloggers to chat and share ideas.',
        'avatar':      avatar('Bloggers Hub'),
        'admin_id':    alice['id'],
        'updated_at':  ts(10),
        'created_at':  ts(10),
    })
    for member in [alice, bob, clara, david, eva]:
        db.group_members.insert({'group_id': group['id'], 'user_id': member['id']})

    group_messages = [
        (alice, "Welcome everyone to Bloggers Hub! 🎉",                    ts(10)),
        (bob,   "Great idea Alice! Looking forward to sharing ideas here.", ts(9, 22)),
        (clara, "Love this group. Can we share drafts here for feedback?",  ts(9, 20)),
        (alice, "Absolutely, that's the whole point!",                      ts(9, 18)),
        (david, "Just posted my LLM intro post. Would love your thoughts.", ts(9, 10)),
        (eva,   "On it! Group blogs-review session is a great idea.",       ts(9,  5)),
    ]
    for sender, text, created in group_messages:
        db.messages.insert({
            'sender_id':   sender['id'],
            'receiver_id': '',
            'group_id':    group['id'],
            'text':        text,
            'is_group':    'True',
            'is_read':     'True',
            'created_at':  created,
        })

    print(f"  ✓ Group '{group['name']}' with {len(group_messages)} messages created")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 48)
    print("  Seed complete!")
    print("=" * 48)
    print(f"  Users     : {len(users)}")
    print(f"  Blogs     : {len(blogs)}")
    print(f"  Likes     : {len(like_data)}")
    print(f"  Comments  : {len(comment_data)}")
    print(f"  Messages  : {len(msg_data) + len(group_messages)}")
    print(f"  Groups    : 1")
    print(f"  Notifs    : {len(notif_data)}")
    print()
    print("  Demo accounts (password: password123)")
    print("  admin@demo.com  alice@demo.com  bob@demo.com")
    print("  clara@demo.com  david@demo.com  eva@demo.com")
    print("=" * 48)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    reset = '--reset' in sys.argv

    if not reset:
        existing = db.users.find_one(email='admin@demo.com')
        if existing:
            print("Database already seeded. Use --reset to clear and reseed.")
            print("  python seed.py --reset")
            sys.exit(0)

    if reset:
        reset_all()

    seed()
