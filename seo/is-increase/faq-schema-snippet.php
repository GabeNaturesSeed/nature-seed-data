/**
 * Nature's Seed — FAQ Schema Injection for Product Categories
 *
 * HOW TO INSTALL:
 * 1. Install "Code Snippets" plugin (free) from WordPress plugin directory
 * 2. Go to Snippets → Add New
 * 3. Name it "FAQ Schema for Categories"
 * 4. Paste this entire code block
 * 5. Set "Run on" to "Frontend only"
 * 6. Click "Save & Activate"
 *
 * OR: Add to your child theme's functions.php
 *
 * This injects FAQPage structured data (JSON-LD) into the <head> of
 * WooCommerce product category pages. Google uses this to display
 * rich FAQ snippets in search results.
 *
 * To update FAQs: Edit the $category_faqs array below.
 */

add_action( 'wp_head', 'ns_inject_category_faq_schema' );

function ns_inject_category_faq_schema() {
    // Only run on product category archive pages
    if ( ! is_product_category() ) {
        return;
    }

    $term = get_queried_object();
    if ( ! $term || ! isset( $term->term_id ) ) {
        return;
    }

    // FAQ data keyed by WooCommerce category ID
    // PLACEHOLDER: This will be populated by the push script with actual FAQ data
    $category_faqs = get_option( 'ns_category_faqs', array() );

    $cat_id = strval( $term->term_id );

    if ( ! isset( $category_faqs[ $cat_id ] ) || empty( $category_faqs[ $cat_id ] ) ) {
        return;
    }

    $faqs = $category_faqs[ $cat_id ];

    // Build FAQPage schema
    $schema = array(
        '@context'   => 'https://schema.org',
        '@type'      => 'FAQPage',
        'mainEntity' => array(),
    );

    foreach ( $faqs as $faq ) {
        $schema['mainEntity'][] = array(
            '@type'          => 'Question',
            'name'           => $faq['question'],
            'acceptedAnswer' => array(
                '@type' => 'Answer',
                'text'  => $faq['answer'],
            ),
        );
    }

    echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . '</script>' . "\n";
}

/**
 * REST API endpoint to update FAQ data programmatically.
 * POST /wp-json/ns/v1/category-faqs
 * Body: {"category_id": "3897", "faqs": [{"question": "...", "answer": "..."}]}
 *
 * Auth: Requires WC API credentials (Basic Auth)
 */
add_action( 'rest_api_init', function() {
    register_rest_route( 'ns/v1', '/category-faqs', array(
        'methods'  => 'POST',
        'callback' => 'ns_update_category_faqs',
        'permission_callback' => function() {
            return current_user_can( 'manage_woocommerce' );
        },
    ));

    register_rest_route( 'ns/v1', '/category-faqs', array(
        'methods'  => 'GET',
        'callback' => function() {
            return rest_ensure_response( get_option( 'ns_category_faqs', array() ) );
        },
        'permission_callback' => function() {
            return current_user_can( 'manage_woocommerce' );
        },
    ));
});

function ns_update_category_faqs( $request ) {
    $params = $request->get_json_params();

    if ( isset( $params['bulk'] ) && is_array( $params['bulk'] ) ) {
        // Bulk update: {"bulk": {"3897": [faqs], "3881": [faqs], ...}}
        $all_faqs = get_option( 'ns_category_faqs', array() );
        foreach ( $params['bulk'] as $cat_id => $faqs ) {
            $all_faqs[ strval( $cat_id ) ] = $faqs;
        }
        update_option( 'ns_category_faqs', $all_faqs );
        return rest_ensure_response( array( 'updated' => count( $params['bulk'] ) ) );
    }

    if ( ! isset( $params['category_id'] ) || ! isset( $params['faqs'] ) ) {
        return new WP_Error( 'missing_params', 'Requires category_id and faqs', array( 'status' => 400 ) );
    }

    $all_faqs = get_option( 'ns_category_faqs', array() );
    $all_faqs[ strval( $params['category_id'] ) ] = $params['faqs'];
    update_option( 'ns_category_faqs', $all_faqs );

    return rest_ensure_response( array(
        'category_id' => $params['category_id'],
        'faq_count'   => count( $params['faqs'] ),
        'status'      => 'saved',
    ));
}
