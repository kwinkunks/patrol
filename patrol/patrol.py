# -*- coding: utf-8 -*-

import mwclient
import re
import time

MAX_TRIES = 5

def tag_page(site, page):

    # Keep track of attempts
    tries = 0
    
    # Do this in a while loop to retry if there's an edit conflict
    while True:
        
        tries += 1
        
        page = site.Pages[page]
        
        # Grab the text on the page
        text = page.edit()

        # Add something to the end of every page, if it's not there already
        if re.search(r'{{[Qq]uality(\|.*?)?}}', text):
            # Remove the tag from the text
            text = re.sub(r'{{[Qq]uality(\|.*?)?}}',r'',text)
            text = re.sub(r'^\n+',r'',text)
            descr = "Untagged for quality by Patrol app"
            print ' - Untagging {0}'.format(page.page_title)
            
        else:
            text = '{{quality}}\n' + text
            descr = "Tagged for quality by Patrol app"
            print ' - Tagging {0}'.format(page.page_title)

		# Save the page back to the wiki
        try:
            page.save(text, descr)
            print ' - Saved {0}'.format(page.page_title)

        except mwclient.EditError:
            if tries == MAX_TRIES:
                print " * Giving up after {0} tries".format(tries)
            else:
                print " * Failed to save {0}: trying again".format(page.page_title)
                time.sleep(2)
                continue

        except mwclient.HTTPRedirectError:
            print " * Failed to save {0}: redirect error".format(page.page_title)
		
        except mwclient.ProtectedPageError:
            print " * Failed to save {0}: page is protected".format(page.page_title)
          
        break
        

def newpages(site, categories=None, threshold=10, days=14):
    
    # Get the list of new pages' titles
    # Using a rather long list comprehension
    print "-- Getting new pages"
    new_pages = [new_page['title'] for new_page in site.recentchanges() if new_page['type'] == u'new' and new_page['ns'] == 0 and (time.gmtime()[7]+time.gmtime()[0]*365 - (new_page['timestamp'][7]+new_page['timestamp'][0]*365)) < days]
    
    if not new_pages:
        print "** Got nothing"
        
    # Build a dict of pages with their scores on various axes
    results = {}
    
    for p in new_pages:
        
        scores = {}
    
        s = " - Evaluating {0}".format(p)
        print s
        
        page = site.Pages[p]
    
        # Skip redirects and subpages.
        if page.redirect or ('/' in p):
            continue

        if categories:
            if p not in [c.page_title for c in page.categories()]:
                print " * Skipping page not in category list,", p.encode('utf-8')
                continue

        # Length: 0 bytes scores 0, 1000 bytes or more scores 5.
        try:
            scores['length'] = min(int(page.length/200),5)
            
        except Exception, e:
            print " * Skipping page, probably deleted,", p.encode('utf-8'), e
            continue
           
        # Categories: 1 per cat, up to max of 3.
        scores['categories'] = min(len([c for c in page.categories()]),3)
        
        # Images: 1 per image, up to a max of 3.
        scores['images'] = min(len([c for c in page.images()]),3)
        
        # Backlinks: 1 per link, up to a max of 3.
        scores['in-links'] = min(len([c for c in page.backlinks()]),3)

        # Links: 1 per link, up to a max of 3.
        scores['out-links'] = min(len([c for c in page.links()]),3)
        
        # Scoring for title case is a bit of a handful
        def score_for_titlecase(string):
            words = filter(None,re.split(r'[ -,\.]',string))
            titlecase = sum([word.istitle() for word in words[1:]])
            total = len(words) - 1.05  # Protect against div by 0
            return int( 5 * titlecase / total )
            
        scores['title case'] = score_for_titlecase(p)

        # The rest of these need the article text to work.
        text = page.edit()
        
        # References: 1 per ref, up to a max of 3.
        scores['references'] = min(len(re.findall(r"<ref>",text)),3)

        # Check if the article is tagged already.
        scores['quality tag'] = bool(re.search(r'{{[Qq]uality(\|.*?)?}}',text))
        
        scores['creator'] = list(page.revisions())[-1]['user']
        
        scores['age'] = time.gmtime()[7]+time.gmtime()[0]*365 - (list(page.revisions())[-1]['timestamp'][7]+list(page.revisions())[-1]['timestamp'][0]*365)
                
        results[p] = scores
        
    # The are the things that will give a final score
    contributors = ['length', 'categories', 'images', 'in-links', 'out-links', 'references']
    
    # Parse the results and generate lists of pages needing attention
    good, bad = {}, {}
    
    best_score = 0
    
    for page, scores in results.iteritems():
        
        # Calculate the total score
        score = sum([scores[c] for c in contributors])
        
        # Calculate a normalized, inverted version of the score
        badness = 10 * (1 - (float(score)/threshold))
        
        scores['total'] = score
        scores['badness'] = round(badness,2)
        
        if score > threshold:
            good[page] = results[page]
            
        if score > best_score:
                best_score = score
                
        if score <= threshold:
            bad[page] = results[page]
            
        scores['problems'] = ", ".join(sorted([k for k,v in scores.iteritems() if v == 0 and k in contributors]))
        if len(scores['problems'].split(',')) > 4: scores['problems'] = 'multiple issues'
        
        red   = hex(int((score / float(threshold)) * (240 - 217) + 217))[2:]
        green = hex(int((score / float(threshold)) * (173 -  83) +  83))[2:]
        blue  = hex(int((score / float(threshold)) * ( 78 -  79) +  79))[2:]
        scores['colour'] = '#' + red + green + blue
    
    # Generate list of pages flagged as possibly named with title case 
    possibly_titlecase = [p for p in results if results[p]['title case']>=2]

    # Generate ordered list of worst pages, scoring under threshold
    worst_new_pages = sorted(bad, key=lambda p : bad[p]['total'])
    
    # Generate ordered list of best pages
    best_new_pages = sorted(good, key=lambda p : good[p]['total'], reverse=True)
    
    print results
    
    print "-- Done scoring, best was {0}, returning to app.".format(best_score)
    
    return worst_new_pages, possibly_titlecase, best_new_pages, results
    
