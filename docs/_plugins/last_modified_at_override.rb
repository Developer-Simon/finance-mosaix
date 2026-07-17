require 'jekyll-last-modified-at'

module Jekyll
  module LastModifiedAt
    class Determinator
      if instance_methods(false).include?(:last_modified_at_time)
        alias_method :last_modified_at_time_without_asset_guard, :last_modified_at_time
      end

      def last_modified_at_time
        return Time.at(0) unless File.exist?(absolute_path_to_article)
        last_modified_at_time_without_asset_guard
      rescue Errno::ENOENT
        Time.at(0)
      end
    end
  end
end
